import uuid
import service.control

from services import fuzzy
from services.test import TestCase
from . import models


class TestOrganizations(TestCase):

    def setUp(self):
        self.client = service.control.Client(
            'organization',
            token='test-token',
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

        response = self.client.call_action(
            'create_organization',
            organization=organization_data,
        )
        self._verify_field_error(response, 'organization.domain', 'DUPLICATE')

    def test_create_team_invalid_owner_id(self):
        organization = self._create_organization()
        team_data = {
            'organization_id': organization.id,
            'owner_id': 'invalid',
            'name': fuzzy.FuzzyText().fuzz(),
        }
        response = self.client.call_action(
            'create_team',
            team=team_data,
        )
        self._verify_field_error(response, 'team.owner_id')

    def test_create_team_invalid_organization_id(self):
        team_data = {
            'organization_id': 'invalid',
            'owner_id': fuzzy.FuzzyUUID().fuzz(),
            'name': fuzzy.FuzzyText().fuzz(),
        }
        response = self.client.call_action(
            'create_team',
            team=team_data,
        )
        self._verify_field_error(response, 'team.organization_id')

    def test_create_team_non_existant_organization(self):
        team_data = {
            'organization_id': fuzzy.FuzzyUUID().fuzz(),
            'owner_id': fuzzy.FuzzyUUID().fuzz(),
            'name': fuzzy.FuzzyText().fuzz(),
        }
        response = self.client.call_action(
            'create_team',
            team=team_data,
        )
        self._verify_field_error(
            response,
            'team.organization_id',
            'DOES_NOT_EXIST',
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
        self.assertEqual(team.path, [team_data['name']])

    def test_create_team_invalid_child_of(self):
        organization = self._create_organization()
        team_data = {
            'organization_id': organization.id,
            'owner_id': fuzzy.FuzzyUUID().fuzz(),
            'name': fuzzy.FuzzyText().fuzz(),
        }
        response = self.client.call_action(
            'create_team',
            team=team_data,
            child_of='invalid',
        )
        self._verify_field_error(response, 'child_of')

    def test_create_team_non_existant_child_of(self):
        organization = self._create_organization()
        team_data = {
            'organization_id': organization.id,
            'owner_id': fuzzy.FuzzyUUID().fuzz(),
            'name': fuzzy.FuzzyText().fuzz(),
        }
        response = self.client.call_action(
            'create_team',
            team=team_data,
            child_of=fuzzy.FuzzyUUID().fuzz(),
        )
        self._verify_field_error(response, 'child_of', 'DOES_NOT_EXIST')

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
        response = self.client.call_action(
            'create_team',
            team=team_data,
            child_of=root_team.id,
        )
        self._verify_field_error(response, 'child_of', 'DOES_NOT_EXIST')

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
        self.assertEqual(team.path, ['E-Staff', 'Engineering'])

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
        response = self.client.call_action(
            'create_address',
            address=self.address_data,
        )
        self._verify_field_error(response, 'address.organization_id')

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
        response = self.client.call_action(
            'delete_address',
            address_id='invalid',
        )
        self._verify_field_error(response, 'address_id')

    def test_delete_address_does_not_exist(self):
        response = self.client.call_action(
            'delete_address',
            address_id=fuzzy.FuzzyUUID().fuzz(),
        )
        self._verify_field_error(response, 'address_id', 'DOES_NOT_EXIST')

    def test_delete_address(self):
        address = self._create_address()
        response = self.client.call_action(
            'delete_address',
            address_id=address.id,
        )
        self.assertTrue(response.success)
        self.assertFalse(models.Address.objects.filter(pk=address.id).exists())

    def test_get_address_invalid_address_id(self):
        response = self.client.call_action(
            'get_address',
            address_id='invalid',
        )
        self._verify_field_error(response, 'address_id')

    def test_get_address_does_not_exist(self):
        response = self.client.call_action(
            'get_address',
            address_id=fuzzy.FuzzyUUID().fuzz(),
        )
        self._verify_field_error(response, 'address_id', 'DOES_NOT_EXIST')

    def test_get_address(self):
        expected = self._create_address()
        response = self.client.call_action(
            'get_address',
            address_id=expected.id,
        )
        self.assertTrue(response.success)
        self._verify_containers(expected, response.result.address)

    def test_get_team_invalid_team_id(self):
        response = self.client.call_action(
            'get_team',
            team_id='invalid',
        )
        self._verify_field_error(response, 'team_id')

    def test_get_team_does_not_exist(self):
        response = self.client.call_action(
            'get_team',
            team_id=fuzzy.FuzzyUUID().fuzz(),
        )
        self._verify_field_error(response, 'team_id', 'DOES_NOT_EXIST')

    def test_get_team(self):
        expected = self._create_team()
        response = self.client.call_action(
            'get_team',
            team_id=expected.id,
        )
        self._verify_containers(expected, response.result.team)

    def test_get_organization_invalid_organization_id(self):
        response = self.client.call_action(
            'get_organization',
            organization_id='invalid',
        )
        self._verify_field_error(response, 'organization_id')

    def test_get_organization_does_not_exist(self):
        response = self.client.call_action(
            'get_organization',
            organization_id=fuzzy.FuzzyUUID().fuzz(),
        )
        self._verify_field_error(response, 'organization_id', 'DOES_NOT_EXIST')

    def test_get_organization(self):
        expected = self._create_organization()
        response = self.client.call_action(
            'get_organization',
            organization_id=expected.id,
        )
        self._verify_containers(expected, response.result.organization)

    def test_get_organization_with_domain_does_not_exist(self):
        response = self.client.call_action(
            'get_organization',
            organization_domain='doesnotexist.com',
        )
        self._verify_field_error(
            response,
            'organization_domain',
            'DOES_NOT_EXIST',
        )

    def test_get_organization_with_domain(self):
        expected = self._create_organization()
        response = self.client.call_action(
            'get_organization',
            organization_domain=expected.domain,
        )
        self._verify_containers(expected, response.result.organization)

    def test_get_teams_invalid_organization_id(self):
        response = self.client.call_action(
            'get_teams',
            organization_id='invalid',
        )
        self._verify_field_error(response, 'organization_id')

    def test_get_teams_does_not_exist(self):
        response = self.client.call_action(
            'get_teams',
            organization_id=fuzzy.FuzzyUUID().fuzz(),
        )
        self._verify_field_error(response, 'organization_id', 'DOES_NOT_EXIST')

    def test_get_teams(self):
        organization = self._create_organization()
        self._create_team_tree(
            organization_id=organization.id,
            levels=4,
        )
        response = self.client.call_action(
            'get_teams',
            organization_id=organization.id,
        )
        self.assertTrue(response.success)
        self.assertTrue(len(response.result.teams), 5)
