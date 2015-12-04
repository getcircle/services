from csv import DictReader
import hashlib
import os

import arrow
import boto3
from django.conf import settings
from django.utils.encoding import smart_text
from protobufs.services.profile import containers_pb2 as profile_containers
import requests
import service.control

from .base import Row
from .users import add_users

DEFAULT_ID_FIELD_NAME = 'employee_id'
DEFAULT_MANGER_ID_FIELD_NAME = 'manager_eid'


def clean_date(value):
    try:
        result = arrow.get(value)
    except arrow.parser.ParserError:
        result = arrow.get(value, 'M/DD/YY')
    return result.format('YYYY-MM-DD')


def get_image_key(image_url):
    return 'profiles/%s' % (
        hashlib.md5(arrow.utcnow().isoformat() + ':' + image_url).hexdigest(),
    )


def transfer_image_to_s3(image_url):
    if not image_url:
        return

    response = requests.get(image_url)
    if response.ok:
        image_key = get_image_key(image_url)
        client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )
        client.put_object(
            Body=response.content,
            Bucket=settings.AWS_S3_MEDIA_BUCKET,
            ContentType='image/png',
            Key=image_key,
        )
        return 'https://s3.amazonaws.com/%s/%s' % (settings.AWS_S3_MEDIA_BUCKET, image_key)


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
        'profile_picture_image_url': {
            'field_name': 'image_url',
            'func': transfer_image_to_s3,
        },
        'is_admin_(0_or_1)': {
            'field_name': 'is_admin',
            'func': lambda x: int(x) == 1,
        },
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
            translation = self.profile_translations.get(key, key)
            value = smart_text(self.data.get(key, '')).strip()
            if isinstance(translation, dict):
                profile_key = translation.get('field_name', key)
                translation_func = translation.get('func')
                if translation_func and callable(translation_func):
                    value = translation_func(value)
            else:
                profile_key = translation

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


def save_profiles(profile_rows, token, email_to_user_dict, id_field_name):
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
            data['authentication_identifier'] = row[id_field_name]

        profiles.append(data)

    client = service.control.Client('profile', token=token)
    response = client.call_action('bulk_create_profiles', profiles=profiles)
    return response.result.profiles


def save_location_members(rows, token, profiles_dict, id_field_name):
    locations = {}
    members = {}
    for row in rows:
        profile = profiles_dict[row[id_field_name]]
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
            action='add_location_members',
            client_kwargs={'token': token},
            location_id=location_id,
            profile_ids=profile_ids,
        )


def save_reporting_details(rows, token, profiles_dict, id_field_name, manager_id_field_name):
    direct_reports = {}
    teams = {}
    client = service.control.Client('organization', token=token)
    for row in rows:
        profile = profiles_dict[row[id_field_name]]

        if row.name_of_team_they_manage.strip():
            teams[profile.id] = row.name_of_team_they_manage

        manager_id = row[manager_id_field_name]
        if manager_id:
            response = client.call_action(
                'get_profile_reporting_details',
                profile_id=profile.id,
            )
            # we don't want to override existing management info (this command
            # should be idempotent)
            if not response.result.manager_profile_id:
                manager = profiles_dict.get(manager_id)
                if not manager:
                    try:
                        manager = service.control.get_object(
                            service='profile',
                            action='get_profile',
                            return_object='profile',
                            client_kwargs={'token': token},
                            authentication_identifier=manager_id,
                        )
                    except service.control.CallActionError:
                        print 'ERROR: manager profile doesn\'t exist: %s' % (manager_id,)
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


def add_profiles(filename, token, id_field_name, manager_id_field_name):
    if not id_field_name:
        id_field_name = DEFAULT_ID_FIELD_NAME

    if not manager_id_field_name:
        manager_id_field_name = DEFAULT_MANGER_ID_FIELD_NAME

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
    profiles = save_profiles(rows, token, users_dict, id_field_name=id_field_name)
    profiles_dict = dict((p.authentication_identifier, p) for p in profiles)

    save_location_members(rows, token, profiles_dict, id_field_name)
    save_reporting_details(rows, token, profiles_dict, id_field_name, manager_id_field_name)


def update_managers(filename, token, id_field_name, manager_id_field_name):
    if not id_field_name:
        id_field_name = DEFAULT_ID_FIELD_NAME

    if not manager_id_field_name:
        manager_id_field_name = DEFAULT_MANGER_ID_FIELD_NAME

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
        authentication_identifiers=list(
            sum([(r[id_field_name], r[manager_id_field_name]) for r in rows], ())
        ),
        control={'paginator': {'page_size': 100}},
    )
    profiles_dict = dict((p.authentication_identifier, p) for p in profiles)

    direct_reports = {}
    for row in rows:
        profile = profiles_dict[row[id_field_name]]
        manager = profiles_dict[row[manager_id_field_name]]
        direct_reports.setdefault(manager.id, []).append(profile.id)

    client = service.control.Client('organization', token=token)
    for profile_id, profile_ids in direct_reports.iteritems():
        client.call_action(
            'add_direct_reports',
            profile_id=profile_id,
            direct_reports_profile_ids=profile_ids,
        )
