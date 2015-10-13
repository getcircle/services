from csv import DictReader
import os

import arrow
from django.utils.encoding import smart_text
from protobufs.services.profile import containers_pb2 as profile_containers
import service.control

from .base import Row
from .users import add_users


def clean_date(value):
    try:
        result = arrow.get(value)
    except arrow.parser.ParserError:
        result = arrow.get(value, 'M/DD/YY')
    return result.format('YYYY-MM-DD')


class ProfileRow(Row):

    field_names = (
        'first_name',
        'last_name',
        'profile_picture_image_url',
        'small_image_url',
        'title',
        'birth_date',
        'hire_date',
        'email',
    )

    contact_method_field_names = (
        'cell_phone',
    )

    profile_translations = {
        'profile_picture_image_url': 'image_url',
    }

    field_names_to_clean = {
        'birth_date': clean_date,
        'hire_date': clean_date,
    }

    contact_method_to_type = {
        'cell_phone': ('Cell Phone', profile_containers.ContactMethodV1.CELL_PHONE)
    }

    def get_protobuf_data(self):
        data = {}
        for key in self.field_names:
            profile_key = self.profile_translations.get(key, key)
            value = smart_text(self.data.get(key, '')).strip()
            if value:
                if key in self.field_names_to_clean:
                    value = self.field_names_to_clean[key](value)
                data[profile_key] = value

        contact_methods = []
        for key in self.contact_method_field_names:
            value = smart_text(self.data[key]).strip()
            if not value:
                continue

            contact_info = self.contact_method_to_type.get(key)
            if not contact_info:
                print 'Unsupported contact method: %s' % (key,)
                continue

            label, contact_method_type = contact_info
            contact_method = {'value': value}
            contact_method['label'] = label
            contact_method['contact_method_type'] = contact_method_type
            contact_methods.append(contact_method)

        data['contact_methods'] = contact_methods
        return data


def save_profiles(profile_rows, token, email_to_user_dict):
    profiles = []
    for row in profile_rows:
        try:
            user = email_to_user_dict.get(row.email)
        except KeyError:
            print 'user not found for: %s' % (row.email,)
            raise

        data = {'user_id': user.id}
        data.update(row.get_protobuf_data())
        if not data.get('authentication_identifier'):
            data['authentication_identifier'] = data['email']

        profiles.append(data)

    client = service.control.Client('profile', token=token)
    response = client.call_action('bulk_create_profiles', profiles=profiles)
    return response.result.profiles


def save_location_members(rows, token, profiles_dict):
    locations = {}
    members = {}
    for row in rows:
        profile = profiles_dict[row.email]
        if row.office_name:
            if row.office_name not in locations:
                location = service.control.get_object(
                    service='organization',
                    action='get_location',
                    return_object='location',
                    client_kwargs={'token': token},
                    name=row.office_name,
                )
                locations[location.name] = location
            location = locations[row.office_name]
            members.setdefault(location.id, []).append(profile.id)

    for location_id, profile_ids in members.iteritems():
        service.control.call_action(
            service='organization',
            action_name='add_location_members',
            client_kwargs={'token': token},
            location_id=location_id,
            profile_ids=profile_ids,
        )


def save_reporting_details(rows, token, profiles_dict):
    direct_reports = {}
    teams = {}
    client = service.control.Client('organization', token=token)
    for row in rows:
        profile = profiles_dict[row.email]

        if row.name_of_team_they_manage.strip():
            teams[profile.id] = row.name_of_team_they_manage

        if row.manager_email:
            response = client.call_action(
                'get_profile_reporting_details',
                profile_id=profile.id,
            )
            # we don't want to override existing management info (this command
            # should be idempotent)
            if not response.result.manager_profile_id:
                manager = profiles_dict.get(row.manager_email)
                if not manager:
                    try:
                        manager = service.control.get_object(
                            service='profile',
                            action='get_profile',
                            return_object='profile',
                            client_kwargs={'token': token},
                            email=row.manager_email,
                        )
                    except service.control.CallActionError:
                        print 'ERROR: manager profile doesn\'t exist: %s' % (row.manager_email,)
                        continue

                direct_reports.setdefault(manager.id, []).append(profile.id)

    for profile_id, profile_ids in direct_reports.iteritems():
        response = client.call_action(
            'add_direct_reports',
            profile_id=profile_id,
            direct_reports_profile_ids=profile_ids,
        )
        team = response.result.team
        if response.result.created:
            try:
                team.name = teams[profile_id]
                client.call_action('update_team', team=team)
            except KeyError:
                pass


def _validate_filename(filename):
    if not os.path.exists(filename):
        raise ValueError('%s does not exist' % (filename,))


def add_profiles(filename, token):
    rows = []
    _validate_filename(filename)
    with open(filename, 'rU') as read_file:
        reader = DictReader(read_file)
        for row_data in reader:
            row = ProfileRow(row_data)
            if not row.is_empty():
                rows.append(row)

    users = add_users([r.email for r in rows], token)
    users_dict = dict((u.primary_email, u) for u in users)
    profiles = save_profiles(rows, token, users_dict)
    profiles_dict = dict((p.email, p) for p in profiles)

    save_location_members(rows, token, profiles_dict)
    save_reporting_details(rows, token, profiles_dict)


def update_managers(filename, token):
    rows = []
    _validate_filename(filename)
    with open(filename, 'rU') as read_file:
        reader = DictReader(read_file)
        for row_data in reader:
            row = Row(row_data)
            if not row.is_empty():
                rows.append(row)

    profiles = service.control.get_object(
        service='profile',
        action='get_profiles',
        return_object='profiles',
        client_kwargs={'token': token},
        emails=list(sum([(r.email, r.manager_email) for r in rows], ())),
        control={'paginator': {'page_size': 100}},
    )
    profiles_dict = dict((p.email, p) for p in profiles)

    direct_reports = {}
    for row in rows:
        profile = profiles_dict[row.email]
        manager = profiles_dict[row.manager_email]
        direct_reports.setdefault(manager.id, []).append(profile.id)

    client = service.control.Client('organization', token=token)
    for profile_id, profile_ids in direct_reports.iteritems():
        client.call_action(
            'add_direct_reports',
            profile_id=profile_id,
            direct_reports_profile_ids=profile_ids,
        )
