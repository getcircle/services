from csv import DictReader

from django.utils.encoding import smart_text
import service.control

from .base import OrganizationParser

DEFAULT_PASSWORD = 'rhlabs123'


class TeamStore(object):

    def __init__(self):
        self.owner_email_to_team = {}
        self.team_to_owner_email = {}
        self.team_to_parent_owner_email = {}

    def store(self, team, owner_email, parent_owner_email):
        try:
            print 'storing team: %s, owner: %s, parent email: %s' % (
                smart_text(team),
                smart_text(owner_email),
                smart_text(parent_owner_email),
            )
        except Exception as e:
            print e
        self.owner_email_to_team[owner_email] = team
        self.team_to_owner_email[team] = owner_email
        self.team_to_parent_owner_email[team] = parent_owner_email

    def get_parent_team(self, team):
        parent_team = None
        parent_owner_email = self.team_to_parent_owner_email[team]
        if parent_owner_email:
            parent_team = self.owner_email_to_team[parent_owner_email]
        return parent_team

    def get_team_owner(self, team):
        return self.team_to_owner_email[team]


class Row(object):

    profile_fields = (
        'first_name',
        'last_name',
        'email',
        'image_url',
        'title',
        'cell_phone',
        'birth_date',
        'hire_date',
    )

    address_fields = (
        'office_name',
        'office_address_1',
        'office_city',
        'office_region',
        'office_postal_code',
        'office_country_code',
        'office_latitude',
        'office_longitude',
    )

    def __init__(self, data):
        self.data = data

    def __getattr__(self, key):
        if key in self.data:
            return smart_text(self.data[key])

        return super(Row, self).__getattr__(key)

    @property
    def address(self):
        address = {}
        for key in self.address_fields:
            address_part = key.split('office_')[1]
            address[address_part] = self.data[key]
        return address

    @property
    def address_composite_key(self):
        values = self.address.values()
        return ':'.join(sorted(values))

    @property
    def profile(self):
        profile = {}
        for key in self.profile_fields:
            profile[key] = smart_text(self.data[key])
        return profile

    def is_team_owner(self):
        return self.owns_team == '1' or self.owns_team == 'True'


class Parser(OrganizationParser):

    def __init__(self, *args, **kwargs):
        super(Parser, self).__init__(*args, **kwargs)
        self.rows = []
        self.addresses = {}
        self.teams = set()
        self.team_store = TeamStore()
        self.saved_locations = {}
        self.saved_teams = {}
        self.saved_users = {}

    def _save_location(self, data):
        address = {
            'organization_id': self.organization.id,
        }
        address.update(data)
        self.debug_log('saving address: %s' % (address,))
        try:
            response = self.organization_client.call_action(
                'create_address',
                address=address,
            )
            address = response.result.address
        except self.organization_client.CallActionError:
            response = self.organization_client.call_action(
                'get_address',
                name=address['name'],
                organization_id=address['organization_id'],
            )
            address = response.result.address

        location = {
            'name': address.name,
            'organization_id': address.organization_id,
            'address': address,
        }
        try:
            response = self.organization_client.call_action('create_location', location=location)
        except self.organization_client.CallActionError:
            response = self.organization_client.call_action(
                'get_location',
                name=location['name'],
                organization_id=location['organization_id'],
            )
        return response.result.location.id

    def _save_users(self, rows):
        users = []
        for row in rows:
            self.debug_log('saving user: %s' % (row.email,))
            users.append({'primary_email': row.email, 'password': DEFAULT_PASSWORD})

        client = service.control.Client('user', token=self.token)
        response = client.call_action('bulk_create_users', users=users)
        return response.result.users

    def _save_team(self, team):
        self.debug_log('saving team: %s' % (team,))
        if team in self.saved_teams:
            return self.saved_teams[team]

        child_of = None
        parent_team_name = self.team_store.get_parent_team(team)
        if parent_team_name is not None:
            child_of = self._save_team(parent_team_name)

        owner_id = self.saved_users[self.team_store.get_team_owner(team)]
        parameters = {
            'team': {
                'name': team,
                'owner_id': owner_id,
                'organization_id': self.organization.id,
            },
            'child_of': child_of,
        }
        self.debug_log('creating team: %s' % (parameters,))
        try:
            response = self.organization_client.call_action(
                'create_team',
                **parameters
            )
            team = response.result.team
        except self.organization_client.CallActionError:
            response = self.organization_client.call_action(
                'get_team',
                name=team,
                organization_id=self.organization.id,
            )
            team = response.result.team

        self.saved_teams[team.name] = team.id
        return self.saved_teams[team.name]

    def _save_profiles(self, rows):
        profiles = []
        for row in rows:
            profile_data = {
                'organization_id': self.organization.id,
                'team_id': self.saved_teams[row.team],
                'location_id': self.saved_locations[row.address_composite_key],
                'user_id': self.saved_users[row.email],
            }
            profile_data.update(row.profile)
            self.debug_log('creating profile: %s' % (profile_data,))
            profiles.append(profile_data)

        client = service.control.Client('profile', token=self.token)
        #try:
            #response = client.call_action('create_profile', profile=profile_data)
            #profile = response.result.profile
        #except client.CallActionError as e:
            #self.debug_log('error creating profile: %s' % (e,))
            ## fetch the profile
            #response = client.call_action('get_profile', user_id=self.saved_users[row.email])
            #profile = response.result.profile

            ## update the profile
            #for key, value in profile_data.iteritems():
                #setattr(profile, key, value)
            #response = client.call_action('update_profile', profile=profile)
            #profile = response.result.profile
        #return profile
        response = client.call_action('bulk_create_profiles', profiles=profiles)
        return response.result.profiles

    def _parse_address(self, row):
        if row.address_composite_key not in self.addresses:
            self.addresses[row.address_composite_key] = row.address

    def _parse_team(self, row):
        self.teams.add(row.team)
        if row.is_team_owner():
            self.team_store.store(
                row.team,
                row.email,
                row.manager_email,
            )

    def _save(self):
        for composite_key, address in self.addresses.iteritems():
            self.saved_locations[composite_key] = self._save_location(address)

        # create users for all the rows
        users = self._save_users(self.rows)
        for user in users:
            self.saved_users[user.primary_email] = user.id

        for team in self.teams:
            self.saved_teams[team] = self._save_team(team)

        # create the profiles
        self._save_profiles(self.rows)

    def _parse_row(self, row):
        self._parse_address(row)
        self._parse_team(row)

    def parse(self, *args, **kwargs):
        with open(self.filename) as csvfile:
            reader = DictReader(csvfile)
            for row_data in reader:
                row = Row(row_data)
                self._parse_row(row)
                self.rows.append(row)

        if kwargs.get('commit'):
            self._save()
