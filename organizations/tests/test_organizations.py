import uuid
import service.control

from services.test import (
    fuzzy,
    mocks,
    TestCase,
)
from .. import (
    factories,
    models,
)


class TestOrganizations(TestCase):

    def setUp(self):
        self.organization = factories.OrganizationFactory.create()
        self.profile = mocks.mock_profile(organization_id=str(self.organization.id))
        self.client = service.control.Client(
            'organization',
            token=mocks.mock_token(
                profile_id=str(self.profile.id),
                organization_id=str(self.organization.id),
            ),
        )
        self.organization_name = 'RH Labs Inc.'
        self.organization_domain = 'rhlabs.com'
        self.address_data = {
            'name': 'Burlingame Office',
            'address_1': '319 Primrose',
            'city': 'Burlingame',
            'region': 'California',
            'postal_code': '94010',
            'country_code': 'US',
            'latitude': '37.578286',
            'longitude': '-122.348729',
            'timezone': 'America/Los_Angeles',
        }

    def _create_organization(self, name=None, domain=None):
        response = self.client.call_action(
            'create_organization',
            organization={
                'name': name or self.organization_name,
                'domain': domain or self.organization_domain,
            }
        )
        self.assertTrue(response.success)
        return response.result.organization

    def _create_team(
            self,
            name=None,
            organization_id=None,
            owner_id=None,
            child_of=None,
        ):
        if name is None:
            name = fuzzy.FuzzyText().fuzz()

        if organization_id is None:
            organization_id = self._create_organization().id

        response = self.client.call_action(
            'create_team',
            team={
                'organization_id': organization_id,
                'owner_id': owner_id or fuzzy.FuzzyUUID().fuzz(),
                'name': name,
            },
            child_of=child_of,
        )
        self.assertTrue(response.success)
        return response.result.team

    def _create_team_tree(self, organization_id, levels, owner_id=None):
        root_team = self._create_team(
            organization_id=organization_id,
            name='Root',
            owner_id=owner_id,
        )
        last_team = root_team
        teams = [root_team]
        for i in xrange(levels):
            last_team = self._create_team(
                organization_id=organization_id,
                name='Team %d' % (i,),
                owner_id=owner_id,
                child_of=last_team.id,
            )
            teams.append(last_team)
        return teams

    def _create_address(self, organization_id=None):
        if organization_id is None:
            organization_id = self._create_organization().id
        self.address_data['organization_id'] = organization_id
        response = self.client.call_action(
            'create_address',
            address=self.address_data,
        )
        self.assertTrue(response.success)
        return response.result.address

    def _mock_get_profile_stats(self, mock, team_ids):
        service = 'profile'
        action = 'get_profile_stats'
        mock_response = mock.get_mockable_response(service, action)
        for team_id in team_ids:
            stat = mock_response.stats.add()
            stat.id = team_id
            stat.count = 5

        mock.instance.register_mock_response(
            service,
            action,
            mock_response,
            mock_regex_lookup=r'%s:%s:.*' % (service, action,),
        )

    def _mock_get_requester_profile(self, mock, profile=None):
        profile = profile or self.profile
        mock.instance.register_mock_object(
            service='profile',
            action='get_profile',
            return_object_path='profile',
            return_object=profile,
            profile_id=profile.id,
        )

    def test_create_organization(self):
        response = self.client.call_action(
            'create_organization',
            organization={
                'name': self.organization_name,
                'domain': self.organization_domain,
            }
        )
        self.assertTrue(response.success)

        organization = response.result.organization
        self.assertTrue(uuid.UUID(organization.id, version=4))
        self.assertEqual(organization.name, self.organization_name)
        self.assertEqual(organization.domain, self.organization_domain)

    def test_create_organization_duplicate_domain(self):
        organization_data = {
            'name': self.organization_name,
            'domain': self.organization_domain,
        }
        response = self.client.call_action(
            'create_organization',
            organization=organization_data,
        )
        self.assertTrue(response.success)

        with self.assertFieldError('organization.domain', 'DUPLICATE'):
            self.client.call_action(
                'create_organization',
                organization=organization_data,
            )

    def test_create_team_invalid_owner_id(self):
        organization = self._create_organization()
        team_data = {
            'organization_id': organization.id,
            'owner_id': 'invalid',
            'name': fuzzy.FuzzyText().fuzz(),
        }
        with self.assertFieldError('team.owner_id'):
            self.client.call_action(
                'create_team',
                team=team_data,
            )

    def test_create_team_invalid_organization_id(self):
        team_data = {
            'organization_id': 'invalid',
            'owner_id': fuzzy.FuzzyUUID().fuzz(),
            'name': fuzzy.FuzzyText().fuzz(),
        }
        with self.assertFieldError('team.organization_id'):
            self.client.call_action(
                'create_team',
                team=team_data,
            )

    def test_create_team_non_existant_organization(self):
        team_data = {
            'organization_id': fuzzy.FuzzyUUID().fuzz(),
            'owner_id': fuzzy.FuzzyUUID().fuzz(),
            'name': fuzzy.FuzzyText().fuzz(),
        }
        with self.assertFieldError('team.organization_id', 'DOES_NOT_EXIST'):
            self.client.call_action(
                'create_team',
                team=team_data,
            )

    def test_create_team_null_child_of_means_root(self):
        owner_id = fuzzy.FuzzyUUID().fuzz()
        organization = self._create_organization()
        team_data = {
            'organization_id': organization.id,
            'owner_id': owner_id,
            'name': fuzzy.FuzzyText().fuzz(),
        }
        response = self.client.call_action(
            'create_team',
            team=team_data,
        )
        self.assertTrue(response.success)

        team = response.result.team
        self.assertTrue(uuid.UUID(team.id, version=4))
        self.assertEqualUUID4(team.organization_id, organization.id)
        self.assertEqual(team.name, team_data['name'])
        self.assertEqualUUID4(team.owner_id, owner_id)
        self.assertEqual([path.name for path in team.path], [team_data['name']])

    def test_create_team_invalid_child_of(self):
        organization = self._create_organization()
        team_data = {
            'organization_id': organization.id,
            'owner_id': fuzzy.FuzzyUUID().fuzz(),
            'name': fuzzy.FuzzyText().fuzz(),
        }
        with self.assertFieldError('child_of'):
            self.client.call_action(
                'create_team',
                team=team_data,
                child_of='invalid',
            )

    def test_create_team_non_existant_child_of(self):
        organization = self._create_organization()
        team_data = {
            'organization_id': organization.id,
            'owner_id': fuzzy.FuzzyUUID().fuzz(),
            'name': fuzzy.FuzzyText().fuzz(),
        }
        with self.assertFieldError('child_of', 'DOES_NOT_EXIST'):
            self.client.call_action(
                'create_team',
                team=team_data,
                child_of=fuzzy.FuzzyUUID().fuzz(),
            )

    def test_create_team_child_of_must_be_in_same_organization(self):
        organization_1 = self._create_organization(domain='first')
        organization_2 = self._create_organization(domain='second')
        root_team = self._create_team(
            organization_id=organization_1.id,
            name='E-Staff',
        )

        team_data = {
            'organization_id': organization_2.id,
            'owner_id': fuzzy.FuzzyUUID().fuzz(),
            'name': fuzzy.FuzzyText().fuzz(),
        }
        with self.assertFieldError('child_of', 'DOES_NOT_EXIST'):
            self.client.call_action(
                'create_team',
                team=team_data,
                child_of=root_team.id,
            )

    def test_create_team_child_of_one_level(self):
        organization = self._create_organization()
        root_team = self._create_team(
            organization_id=organization.id,
            name='E-Staff',
        )

        response = self.client.call_action(
            'create_team',
            team={
                'organization_id': organization.id,
                'owner_id': fuzzy.FuzzyUUID().fuzz(),
                'name': 'Engineering',
            },
            child_of=root_team.id,
        )
        self.assertTrue(response.success)
        team = response.result.team
        self.assertEqual(team.organization_id, organization.id)
        self.assertEqual(team.name, 'Engineering')
        self.assertEqual([path.name for path in team.path], ['E-Staff', 'Engineering'])

    def test_create_team_child_of_multiple_levels(self):
        organization = self._create_organization()
        teams = self._create_team_tree(
            organization_id=organization.id,
            levels=4,
        )
        self.assertEqual(len(teams[-1].path), 5)

    def test_team_protobuf_department(self):
        organization = self._create_organization()
        teams = self._create_team_tree(
            organization_id=organization.id,
            levels=4,
        )
        department_team = teams[1]
        team = teams[-1]
        self.assertEqual(department_team.name, team.department)

    # XXX we may actually want to support this
    #def test_create_team_root_already_exists(self):
        #organization_id = uuid.uuid4().hex
        #action_response, _ = self.client.call_action(
            #'create_team',
            #organization_id=organization_id,
            #owner_id=uuid.uuid4().hex,
            #name='E-Staff',
        #)
        #self.assertTrue(action_response.result.success)

        #action_response, _ = self.client.call_action(
            #'create_team',
            #organization_id=organization_id,
            #owner_id=uuid.uuid4().hex,
            #name='Board of Directors',
        #)
        #self.assertFalse(action_response.result.success)
        #self.assertIn('ROOT_ALREADY_EXISTS', action_response.result.errors)

    def test_create_address_invalid_organization_id(self):
        self.address_data['organization_id'] = 'invalid'
        with self.assertFieldError('address.organization_id'):
            self.client.call_action(
                'create_address',
                address=self.address_data,
            )

    def test_create_address(self):
        organization = self._create_organization()
        self.address_data['organization_id'] = organization.id
        response = self.client.call_action(
            'create_address',
            address=self.address_data,
        )
        self.assertTrue(response.success)
        for key, value in self.address_data.iteritems():
            self.assertEqual(getattr(response.result.address, key), value)

    def test_delete_address_invalid_address_id(self):
        with self.assertFieldError('address_id'):
            self.client.call_action(
                'delete_address',
                address_id='invalid',
            )

    def test_delete_address_does_not_exist(self):
        with self.assertFieldError('address_id', 'DOES_NOT_EXIST'):
            self.client.call_action(
                'delete_address',
                address_id=fuzzy.FuzzyUUID().fuzz(),
            )

    def test_delete_address(self):
        address = self._create_address()
        response = self.client.call_action(
            'delete_address',
            address_id=address.id,
        )
        self.assertTrue(response.success)
        self.assertFalse(models.Address.objects.filter(pk=address.id).exists())

    def test_get_address_invalid_address_id(self):
        with self.assertFieldError('address_id'):
            self.client.call_action(
                'get_address',
                address_id='invalid',
            )

    def test_get_address_does_not_exist(self):
        with self.assertFieldError('address_id', 'DOES_NOT_EXIST'):
            self.client.call_action(
                'get_address',
                address_id=fuzzy.FuzzyUUID().fuzz(),
            )

    def test_get_address(self):
        expected = self._create_address()
        response = self.client.call_action(
            'get_address',
            address_id=expected.id,
        )
        self.assertTrue(response.success)
        self.verify_containers(expected, response.result.address)

    def test_get_addresses_invalid_organization_id(self):
        with self.assertFieldError('organization_id'):
            self.client.call_action(
                'get_addresses',
                organization_id='invalid',
            )

    def test_get_addresses(self):
        organization = self._create_organization()
        for _ in range(1):
            self._create_address(organization_id=organization.id)

        response = self.client.call_action(
            'get_addresses',
            organization_id=organization.id,
        )
        self.assertTrue(response.success)
        self.assertTrue(len(response.result.addresses), 2)

    def test_get_team_invalid_team_id(self):
        with self.assertFieldError('team_id'):
            self.client.call_action(
                'get_team',
                team_id='invalid',
            )

    def test_get_team_does_not_exist(self):
        with self.assertFieldError('team_id', 'DOES_NOT_EXIST'):
            self.client.call_action(
                'get_team',
                team_id=fuzzy.FuzzyUUID().fuzz(),
            )

    def test_get_team(self):
        expected = self._create_team()
        with self.mock_transport() as mock:
            self._mock_get_profile_stats(mock, [expected.id])
            self._mock_get_requester_profile(mock)
            response = self.client.call_action(
                'get_team',
                team_id=expected.id,
            )
        self.verify_containers(expected, response.result.team)
        self.assertEqual(response.result.team.profile_count, 5)

    def test_get_organization_invalid_organization_id(self):
        with self.assertFieldError('organization_id'):
            self.client.call_action(
                'get_organization',
                organization_id='invalid',
            )

    def test_get_organization_does_not_exist(self):
        with self.assertFieldError('organization_id', 'DOES_NOT_EXIST'):
            self.client.call_action(
                'get_organization',
                organization_id=fuzzy.FuzzyUUID().fuzz(),
            )

    def test_get_organization(self):
        expected = self._create_organization()
        response = self.client.call_action(
            'get_organization',
            organization_id=expected.id,
        )
        self.verify_containers(expected, response.result.organization)

    def test_get_organization_with_domain_does_not_exist(self):
        with self.assertFieldError('organization_domain', 'DOES_NOT_EXIST'):
            self.client.call_action('get_organization', organization_domain='doesnotexist.com')

    def test_get_organization_with_domain(self):
        expected = self._create_organization()
        response = self.client.call_action(
            'get_organization',
            organization_domain=expected.domain,
        )
        self.verify_containers(expected, response.result.organization)

    def test_get_teams(self):
        profile = mocks.mock_profile(organization_id=str(self.organization.id), is_admin=True)
        teams = self._create_team_tree(
            organization_id=str(self.organization.id),
            levels=4,
        )

        self.client.token = mocks.mock_token(
            profile_id=profile.id,
            organization_id=str(self.organization.id),
        )
        with self.mock_transport() as mock:
            self._mock_get_profile_stats(mock, [team.id for team in teams])
            self._mock_get_requester_profile(mock, profile=profile)
            response = self.client.call_action('get_teams')

        self.assertTrue(response.success)
        self.assertTrue(len(response.result.teams), 5)
        for team in response.result.teams:
            self.assertTrue(team.permissions.can_edit)
            self.assertTrue(team.permissions.can_add)
            self.assertTrue(team.permissions.can_delete)

    def test_get_teams_by_location_id(self):
        location_id = fuzzy.FuzzyUUID().fuzz()
        organization = factories.OrganizationFactory.create()
        teams = factories.TeamFactory.create_batch(2, organization=organization)
        with self.mock_transport() as mock:
            self._mock_get_requester_profile(mock)
            self._mock_get_profile_stats(mock, [str(team.id) for team in teams])
            mock_response = mock.get_mockable_response('profile', 'get_attributes_for_profiles')
            for team in teams:
                attribute = mock_response.attributes.add()
                attribute.name = 'team_id'
                attribute.value = str(team.id)
            mock.instance.register_mock_response(
                'profile',
                'get_attributes_for_profiles',
                mock_response,
                location_id=location_id,
                distinct=True,
                attributes=['team_id'],
            )
            response = self.client.call_action('get_teams', location_id=location_id)
        self.assertEqual(len(response.result.teams), 2)

    def test_get_teams_invalid_location_id(self):
        with self.assertFieldError('location_id'):
            self.client.call_action('get_teams', location_id='invalid')

    def test_get_team_descendants_invalid_team_id(self):
        with self.assertFieldError('team_ids'):
            self.client.call_action('get_team_descendants', team_ids=['invalid'])

    def test_get_team_descendants_team_ids_required(self):
        with self.assertFieldError('team_ids', 'MISSING'):
            self.client.call_action('get_team_descendants')

    def _setup_team_with_descendants(self):
        parent_team = self._create_team()

        # create child teams
        self._create_team(
            name='b',
            organization_id=parent_team.organization_id,
            child_of=parent_team.id,
        )
        second_child_team = self._create_team(
            name='a',
            organization_id=parent_team.organization_id,
            child_of=parent_team.id,
        )

        # create grandchild team
        self._create_team(
            name='c',
            organization_id=second_child_team.organization_id,
            child_of=second_child_team.id,
        )
        return parent_team

    def test_get_team_descendants_depth_1(self):
        parent_team = self._setup_team_with_descendants()
        # verify only child teams are returned
        with self.mock_transport() as mock:
            self._mock_get_requester_profile(mock)
            response = self.client.call_action(
                'get_team_descendants',
                team_ids=[parent_team.id],
                depth=1,
            )

        descendants = response.result.descendants[0]
        self.assertEqual(descendants.parent_team_id, parent_team.id)
        self.assertEqual(len(descendants.teams), 2)
        self.assertEqual(descendants.teams[0].name, 'a')
        self.assertEqual(descendants.teams[1].name, 'b')

    def test_get_team_descendants_invalid_depth(self):
        team = factories.TeamFactory.create()
        with self.assertRaises(ValueError):
            self.client.call_action('get_team_descendants', team_ids=[str(team.id)], depth=-1)

        with self.assertRaises(TypeError):
            self.client.call_action(
                'get_team_descendants',
                team_ids=[str(team.id)],
                depth='invalid',
            )

    def test_get_team_descendants(self):
        profile = mocks.mock_profile(is_admin=True)
        parent_team = self._setup_team_with_descendants()
        self.client.token = mocks.mock_token(profile_id=profile.id)
        with self.mock_transport() as mock:
            self._mock_get_requester_profile(mock, profile=profile)
            response = self.client.call_action('get_team_descendants', team_ids=[parent_team.id])

        descendants = response.result.descendants[0]
        self.assertEqual(len(descendants.teams), 3)
        self.assertEqual(descendants.teams[0].name, 'a')
        self.assertEqual(descendants.teams[1].name, 'b')
        for team in descendants.teams:
            self.assertTrue(team.permissions.can_edit)
            self.assertTrue(team.permissions.can_add)
            self.assertTrue(team.permissions.can_delete)

    def test_get_team_descendants_multiple_teams(self):
        # create 2 teams with descendants
        parent_team_1 = self._create_team()
        # create child teams
        self._create_team(
            name='b',
            organization_id=parent_team_1.organization_id,
            child_of=parent_team_1.id,
        )
        second_child_team = self._create_team(
            name='a',
            organization_id=parent_team_1.organization_id,
            child_of=parent_team_1.id,
        )

        # create grandchild team
        self._create_team(
            name='c',
            organization_id=second_child_team.organization_id,
            child_of=second_child_team.id,
        )

        parent_team_2 = self._create_team(organization_id=parent_team_1.organization_id)
        # create child teams
        self._create_team(
            name='d',
            organization_id=parent_team_2.organization_id,
            child_of=parent_team_2.id,
        )
        second_child_team = self._create_team(
            name='e',
            organization_id=parent_team_2.organization_id,
            child_of=parent_team_2.id,
        )

        # create grandchild team
        self._create_team(
            name='f',
            organization_id=second_child_team.organization_id,
            child_of=second_child_team.id,
        )

        with self.mock_transport() as mock:
            self._mock_get_requester_profile(mock)
            response = self.client.call_action(
                'get_team_descendants',
                team_ids=[parent_team_1.id, parent_team_2.id, second_child_team.id],
            )
        descendants_1 = response.result.descendants[0]
        self.assertEqual(len(descendants_1.teams), 3)
        self.assertEqual(descendants_1.teams[0].name, 'a')
        self.assertEqual(descendants_1.teams[1].name, 'b')

        descendants_2 = response.result.descendants[1]
        self.assertEqual(len(descendants_2.teams), 3)
        self.assertEqual(descendants_2.teams[0].name, 'd')
        self.assertEqual(descendants_2.teams[1].name, 'e')

        descendants_3 = response.result.descendants[2]
        self.assertEqual(len(descendants_3.teams), 1)
        self.assertEqual(descendants_3.teams[0].name, 'f')

    def test_get_team_descendants_specific_attributes(self):
        parent_team = self._setup_team_with_descendants()
        response = self.client.call_action(
            'get_team_descendants',
            team_ids=[parent_team.id],
            attributes=['id', 'name'],
        )

        descendants = response.result.descendants[0]
        self.assertEqual(len(descendants.teams), 3)
        for team in descendants.teams:
            fields = team.ListFields()
            self.assertEqual(len(fields), 2)
            self.assertTrue(fields[0][0].name, 'id')
            self.assertTrue(fields[1][0].name, 'name')

    def test_get_team_descendants_invalid_attributes(self):
        team = self._create_team()
        with self.assertFieldError('attributes'):
            self.client.call_action(
                'get_team_descendants',
                team_ids=[team.id],
                attributes=['invalid', '; drop schema public;'],
            )

    def test_create_team_duplicate_name(self):
        team = factories.TeamFactory.create()
        team_dict = team.as_dict()
        clear_keys = ['id', 'created', 'changed', 'path']
        for key in clear_keys:
            team_dict.pop(key)

        with self.assertFieldError('team.name', 'DUPLICATE'):
            self.client.call_action('create_team', team=team_dict)

    def test_get_team_with_name_and_organization_id_organization_id_invalid(self):
        with self.assertFieldError('organization_id'):
            self.client.call_action('get_team', name='test', organization_id='invalid')

    def test_get_team_with_name_and_organization_id_only_name_provided(self):
        with self.assertFieldError('organization_id', 'MISSING'):
            self.client.call_action('get_team', name='test')

    def test_get_team_with_name_and_organization_id(self):
        team = factories.TeamFactory.create()
        with self.mock_transport() as mock:
            self._mock_get_profile_stats(mock, [str(team.id)])
            self._mock_get_requester_profile(mock)
            response = self.client.call_action(
                'get_team',
                name=team.name,
                organization_id=str(team.organization_id),
            )
        self.assertTrue(response.success)
        self.assertTrue(str(team.id), response.result.team.id)

    def test_create_address_duplicate(self):
        address = factories.AddressFactory.create()
        with self.assertFieldError('address.name', 'DUPLICATE'):
            self.client.call_action(
                'create_address',
                address=address.as_dict(exclude=('id', 'created', 'changed')),
            )

    def test_get_address_name_and_organization_organization_id_invalid(self):
        with self.assertFieldError('organization_id'):
            self.client.call_action('get_address', name='test', organization_id='invalid')

    def test_get_address_name_and_organization_organization_required_if_name(self):
        with self.assertFieldError('organization_id', 'MISSING'):
            self.client.call_action('get_address', name='test')

    def test_get_address_name_and_organization_id(self):
        address = factories.AddressFactory.create_protobuf()
        response = self.client.call_action(
            'get_address',
            name=address.name,
            organization_id=address.organization_id,
        )
        self.assertTrue(response.success)
        self.verify_containers(address, response.result.address)

    def test_get_top_level_team(self):
        parent_team = self._create_team(organization_id=str(self.organization.id))

        # create children teams
        for _ in range(2):
            child_team = self._create_team(
                organization_id=parent_team.organization_id,
                child_of=parent_team.id,
            )

        # create a grandchild team
        self._create_team(organization_id=child_team.organization_id, child_of=child_team.id)

        response = self.client.call_action('get_top_level_team')
        self.verify_containers(parent_team, response.result.team)

    def test_get_teams_top_level_only(self):
        profile = mocks.mock_profile(organization_id=str(self.organization.id), is_admin=True)
        parent_team = self._create_team(organization_id=str(self.organization.id))

        teams = []
        # create children teams
        for _ in range(2):
            child_team = self._create_team(
                organization_id=parent_team.organization_id,
                child_of=parent_team.id,
            )
            teams.append(child_team)

        # create a grandchild team
        self._create_team(organization_id=child_team.organization_id, child_of=child_team.id)

        self.client.token = mocks.mock_token(
            profile_id=profile.id,
            organization_id=str(self.organization.id),
        )
        with self.mock_transport() as mock:
            mock.instance.dont_mock_service('organization')
            self._mock_get_profile_stats(mock, [team.id for team in teams])
            self._mock_get_requester_profile(mock, profile=profile)
            response = self.client.call_action('get_teams', top_level_only=True)
        self.assertEqual(len(response.result.teams), 3)
        self.verify_containers(parent_team, response.result.teams[0])

    def test_get_team_include_permissions_not_admin(self):
        team = factories.TeamFactory.create()
        with self.mock_transport() as mock:
            self._mock_get_profile_stats(mock, [str(team.id)])
            self._mock_get_requester_profile(mock)
            response = self.client.call_action('get_team', team_id=str(team.id))
        team = response.result.team
        self.assertFalse(team.permissions.can_add)
        self.assertFalse(team.permissions.can_edit)
        self.assertFalse(team.permissions.can_delete)

    def test_get_team_include_permissions_admin(self):
        team = factories.TeamFactory.create()
        profile = mocks.mock_profile(organization_id=str(team.organization_id), is_admin=True)
        token = mocks.mock_token(organization_id=team.organization_id, profile_id=profile.id)
        self.client.token = token
        with self.mock_transport() as mock:
            self._mock_get_profile_stats(mock, [str(team.id)])
            self._mock_get_requester_profile(mock, profile=profile)
            response = self.client.call_action('get_team', team_id=str(team.id))
        team = response.result.team
        self.assertTrue(team.permissions.can_add)
        self.assertTrue(team.permissions.can_edit)
        self.assertTrue(team.permissions.can_delete)

    def test_update_team_team_required(self):
        with self.assertFieldError('team', 'MISSING'):
            self.client.call_action('update_team')

    def test_update_team_team_does_not_exist(self):
        with self.assertFieldError('team.id', 'DOES_NOT_EXIST'):
            self.client.call_action('update_team', team=mocks.mock_team())

    def test_update_team_profile_admin(self):
        self.profile.is_admin = True
        team = factories.TeamFactory.create(organization=self.organization)
        container = team.to_protobuf(path=team.get_path())
        container.name = 'new name'
        container.description = 'new description'
        with self.mock_transport() as mock:
            mock.instance.register_empty_response(
                service='history',
                action='record_action',
                mock_regex_lookup='history:record_action:.*',
            )
            mock.instance.register_mock_object(
                service='profile',
                action='get_profile',
                return_object_path='profile',
                return_object=self.profile,
                profile_id=self.profile.id,
            )
            response = self.client.call_action('update_team', team=container)
        self.assertEqual(response.result.team.name, container.name)
        self.assertTrue(response.result.team.permissions.can_edit)
        self.assertTrue(response.result.team.permissions.can_add)
        self.assertTrue(response.result.team.permissions.can_delete)

        team = models.Team.objects.get(pk=team.id)
        self.assertEqual(team.name, container.name)

    def test_update_team_profile_non_admin(self):
        self.profile.is_admin = False
        team = factories.TeamFactory.create(organization=self.organization)
        container = team.to_protobuf(path=team.get_path())
        container.name = 'new name'
        with self.mock_transport() as mock, self.assertRaisesCallActionError() as expected:
            mock.instance.register_mock_object(
                service='profile',
                action='get_profile',
                return_object_path='profile',
                return_object=self.profile,
                profile_id=self.profile.id,
            )
            self.client.call_action('update_team', team=container)

        self.assertIn('PERMISSION_DENIED', expected.exception.response.errors)

    def test_update_team_non_editable_fields(self):
        self.profile.is_admin = True
        team = factories.TeamFactory.create(organization=self.organization)
        container = team.to_protobuf(path=team.get_path())
        container.organization_id = fuzzy.FuzzyUUID().fuzz()
        container.owner_id = fuzzy.FuzzyUUID().fuzz()
        container.name = 'new name'
        with self.mock_transport() as mock:
            mock.instance.register_mock_object(
                service='profile',
                action='get_profile',
                return_object_path='profile',
                return_object=self.profile,
                profile_id=self.profile.id,
            )
            response = self.client.call_action('update_team', team=container)

        updated_team = response.result.team
        self.assertNotEqual(updated_team.organization_id, container.organization_id)
        self.assertNotEqual(updated_team.owner_id, container.owner_id)
        self.assertEqual(updated_team.name, container.name)
