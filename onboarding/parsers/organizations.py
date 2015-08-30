from csv import DictReader

from django.contrib.auth.hashers import make_password
from django.utils.encoding import smart_text
from protobufs.services.profile import containers_pb2 as profile_containers
import service.control

from services.utils import get_timezone_for_location
from .base import OrganizationParser

DEFAULT_PASSWORD = make_password('rhlabs')


class Row(object):

    profile_fields = (
        'first_name',
        'last_name',
        'image_url',
        'small_image_url',
        'title',
        'birth_date',
        'hire_date',
        'email',
    )

    contact_method_fields = (
        'cell_phone',
    )

    location_fields = (
        'office_name',
        'office_address_1',
        'office_city',
        'office_region',
        'office_postal_code',
        'office_country_code',
        'office_latitude',
        'office_longitude',
        'office_image_url',
    )

    def __init__(self, data):
        self.data = data

    def __getattr__(self, key):
        if key in self.data:
            return smart_text(self.data[key])

        return super(Row, self).__getattr__(key)

    @property
    def location(self):
        location = {}
        for key in self.location_fields:
            location_part = key.split('office_')[1]
            location[location_part] = self.data[key]
        return location

    @property
    def location_composite_key(self):
        values = self.location.values()
        return ':'.join(sorted(values))

    @property
    def profile(self):
        profile = {}
        for key in self.profile_fields:
            if key in self.data:
                profile[key] = smart_text(self.data[key])

        contact_methods = []
        for key in self.contact_method_fields:
            contact_method = {'value': smart_text(self.data[key])}
            contact_method['label'] = 'Cell Phone'
            contact_method['contact_method_type'] = profile_containers.ContactMethodV1.CELL_PHONE
            contact_methods.append(contact_method)

        profile['contact_methods'] = contact_methods
        return profile

    def is_team_owner(self):
        return self.owns_team == '1' or self.owns_team == 'True' or self.owns_team == 'TRUE'


class Parser(OrganizationParser):

    def __init__(self, *args, **kwargs):
        super(Parser, self).__init__(*args, **kwargs)
        self.locations = {}
        self.direct_reports = {}
        self.saved_profiles = {}
        self.saved_users = {}
        self.saved_locations = {}
        self.profile_id_to_profile = {}

    def _save_location(self, data):
        location = {
            'organization_id': self.organization.id,
            'timezone': get_timezone_for_location(data['latitude'], data['longitude']),
        }
        location.update(data)
        location.pop('image_url')
        self.debug_log('saving location: %s' % (location,))
        try:
            response = self.organization_client.call_action(
                'create_location',
                location=location,
            )
        except service.control.CallActionError:
            # XXX make `get_location` take name
            response = self.organization_client.call_action('get_location', name=location['name'])
        return response.result.location

    def _save_users(self, rows):
        users = []
        for row in rows:
            self.debug_log('saving user: %s' % (row.email,))
            users.append({'primary_email': row.email, 'password': DEFAULT_PASSWORD})

        client = service.control.Client('user', token=self.token)
        response = client.call_action('bulk_create_users', users=users)
        return response.result.users

    def _save_profiles(self, rows):
        profiles = []
        for row in rows:
            profile_data = {
                'organization_id': self.organization.id,
                'user_id': self.saved_users[row.email].id,
            }
            profile_data.update(row.profile)
            self.debug_log('creating profile: %s' % (profile_data,))
            profiles.append(profile_data)

        client = service.control.Client('profile', token=self.token)
        response = client.call_action('bulk_create_profiles', profiles=profiles)
        return response.result.profiles

    def _parse_location(self, row):
        if row.location_composite_key not in self.locations:
            self.locations[row.location_composite_key] = row.location

    def _save(self, rows):
        for composite_key, location in self.locations.iteritems():
            if any(location.values()):
                self.saved_locations[composite_key] = self._save_location(location)

        # create users for all the rows
        users = self._save_users(rows)
        for user in users:
            self.saved_users[user.primary_email] = user

        # create the profiles
        profiles = self._save_profiles(rows)
        for profile in profiles:
            self.saved_profiles[profile.email] = profile
            self.profile_id_to_profile[profile.id] = profile

        direct_reports = {}
        teams = {}
        locations = {}
        for row in rows:
            profile = self.saved_profiles[row.email]
            manager = self.saved_profiles.get(row.manager_email)
            location = self.saved_locations[row.location_composite_key]
            locations.setdefault(location.id, []).append(profile.id)
            if row.is_team_owner():
                teams[profile.id] = row.team
            if manager:
                direct_reports.setdefault(manager.id, []).append(profile.id)

        for profile_id, profile_ids in direct_reports.iteritems():
            response = self.organization_client.call_action(
                'add_direct_reports',
                profile_id=profile_id,
                direct_reports_profile_ids=profile_ids,
            )

            team = response.result.team
            try:
                team.name = teams[profile_id]
                self.organization_client.call_action('update_team', team=team)
            except KeyError:
                pass

        for location_id, profile_ids in locations.iteritems():
            self.organization_client.call_action(
                'add_location_members',
                location_id=location_id,
                profile_ids=profile_ids,
            )

    def parse(self, *args, **kwargs):
        rows = []
        with open(self.filename) as csvfile:
            reader = DictReader(csvfile)
            for row_data in reader:
                row = Row(row_data)
                self._parse_location(row)
                rows.append(row)

        if kwargs.get('commit'):
            self._save(rows)
