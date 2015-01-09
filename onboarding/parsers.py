from csv import DictReader

import service.control


class ParseError(Exception):
    pass


class TeamStore(object):

    def __init__(self):
        self.owner_email_to_team = {}
        self.team_to_owner_email = {}
        self.team_to_parent_owner_email = {}

    def store(self, team, owner_email, parent_owner_email):
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
    )

    address_fields = (
        'office_address_1',
        'office_city',
        'office_region',
        'office_postal_code',
        'office_country_code',
    )

    def __init__(self, data):
        self.data = data

    def __getattr__(self, key):
        if key in self.data:
            return self.data[key]

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
            profile[key] = self.data[key]
        return profile

    def is_team_owner(self):
        return self.owns_team == '1'


class Parser(object):

    def __init__(self, organization_domain, filename, token, verbose=False):
        self.filename = filename
        self.token = token
        self.verbose = verbose

        self.organization_domain = organization_domain
        self.organization = self._fetch_organization()

        self.rows = []
        self.addresses = {}
        self.teams = set()
        self.team_store = TeamStore()
        self.saved_addresses = {}
        self.saved_teams = {}
        self.saved_users = {}

    def debug_log(self, message):
        if self.verbose:
            print message

    @property
    def organization_client(self):
        if not hasattr(self, '_organization_client'):
            self._organization_client = service.control.Client(
                'organization',
                token=self.token,
            )
        return self._organization_client

    def _fetch_organization(self):
        response = self.organization_client.call_action(
            'get_organization',
            organization_domain=self.organization_domain,
        )
        return response.result.organization

    def _save_address(self, data):
        address = {
            'organization_id': self.organization.id,
        }
        address.update(data)
        self.debug_log('saving address: %s' % (address,))
        response = self.organization_client.call_action(
            'create_address',
            address=address,
        )
        return response.result.address.id

    def _save_user(self, row):
        self.debug_log('saving user: %s' % (row.email,))
        client = service.control.Client('user', token=self.token)
        response = client.call_action('create_user', email=row.email, password='rhlabs123')
        if response.success:
            user = response.result.user
        else:
            response = client.call_action('get_user', email=row.email)
            user = response.result.user
        return user.id

    def _save_team(self, team):
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
        response = self.organization_client.call_action(
            'create_team',
            **parameters
        )
        if response.success:
            team = response.result.team
        else:
            response = self.organization_client.call_action(
                'get_team',
                name=team,
                organization_id=self.organization.id,
            )
            team = response.result.team

        self.saved_teams[team.name] = team.id
        return self.saved_teams[team.name]

    def _save_profile(self, row):
        profile_data = {
            'organization_id': self.organization.id,
            'team_id': self.saved_teams[row.team],
            'address_id': self.saved_addresses[row.address_composite_key],
            'user_id': self.saved_users[row.email],
        }
        profile_data.update(row.profile)
        self.debug_log('creating profile: %s' % (profile_data,))
        client = service.control.Client('profile', token=self.token)
        response = client.call_action('create_profile', profile=profile_data)
        profile = response.result.profile
        if not response.success:
            self.debug_log('error creating profile: %s' % (response.errors,))
            # fetch the profile
            response = client.call_action('get_profile', user_id=self.saved_users[row.email])
            profile = response.result.profile

            # update the profile
            for key, value in profile_data.iteritems():
                setattr(profile, key, value)
            response = client.call_action('update_profile', profile=profile)
            profile = response.result.profile
        return profile

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
            self.saved_addresses[composite_key] = self._save_address(address)

        # create users for all the rows
        for row in self.rows:
            self.saved_users[row.email] = self._save_user(row)

        for team in self.teams:
            self.saved_teams[team] = self._save_team(team)

        # create the profiles
        for row in self.rows:
            self._save_profile(row)

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
