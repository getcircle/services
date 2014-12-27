import uuid
import service.control

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
            name=name or self.organization_name,
            domain=domain or self.organization_domain,
        )
        self.assertTrue(response.success)
        return response.result.organization

    def _create_team(
            self,
            name,
            organization_id=None,
            owner_id=None,
            child_of=None,
        ):
        if organization_id is None:
            organization_id = self._create_organization().id

        response = self.client.call_action(
            'create_team',
            organization_id=organization_id,
            owner_id=owner_id or uuid.uuid4().hex,
            name=name,
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
            name=self.organization_name,
            domain=self.organization_domain,
        )
        self.assertTrue(response.success)

        organization = response.result.organization
        self.assertTrue(uuid.UUID(organization.id, version=4))
        self.assertEqual(organization.name, self.organization_name)
        self.assertEqual(organization.domain, self.organization_domain)

    def test_create_organization_duplicate_domain(self):
        response = self.client.call_action(
            'create_organization',
            name=self.organization_name,
            domain=self.organization_domain,
        )
        self.assertTrue(response.success)

        response = self.client.call_action(
            'create_organization',
            name=self.organization_name,
            domain=self.organization_domain,
        )
        self._verify_field_error(response, 'domain', 'DUPLICATE')

    def test_create_team_invalid_owner_id(self):
        organization = self._create_organization()
        response = self.client.call_action(
            'create_team',
            organization_id=organization.id,
            owner_id='invalid',
            name='E-Staff',
        )
        self._verify_field_error(response, 'owner_id')

    def test_create_team_invalid_organization_id(self):
        response = self.client.call_action(
            'create_team',
            organization_id='invalid',
            owner_id=uuid.uuid4().hex,
            name='E-Staff',
        )
        self._verify_field_error(response, 'organization_id')

    def test_create_team_non_existant_organization(self):
        response = self.client.call_action(
            'create_team',
            organization_id=uuid.uuid4().hex,
            owner_id=uuid.uuid4().hex,
            name='E-Staff',
        )
        self._verify_field_error(
            response,
            'organization_id',
            'DOES_NOT_EXIST',
        )

    def test_create_team_null_child_of_means_root(self):
        owner_id = uuid.uuid4().hex
        organization = self._create_organization()
        response = self.client.call_action(
            'create_team',
            organization_id=organization.id,
            owner_id=owner_id,
            name='E-Staff'
        )
        self.assertTrue(response.success)

        team = response.result.team
        self.assertTrue(uuid.UUID(team.id, version=4))
        self.assertEqual(team.organization_id, organization.id)
        self.assertEqual(team.name, 'E-Staff')
        self.assertEqual(team.owner_id, owner_id)
        self.assertEqual(team.path, ['E-Staff'])

    def test_create_team_invalid_child_of(self):
        organization = self._create_organization()
        response = self.client.call_action(
            'create_team',
            organization_id=organization.id,
            owner_id=uuid.uuid4().hex,
            name='Engineering',
            child_of='invalid',
        )
        self._verify_field_error(response, 'child_of')

    def test_create_team_non_existant_child_of(self):
        organization = self._create_organization()
        response = self.client.call_action(
            'create_team',
            organization_id=organization.id,
            owner_id=uuid.uuid4().hex,
            name='Engineering',
            child_of=uuid.uuid4().hex,
        )
        self._verify_field_error(response, 'child_of', 'DOES_NOT_EXIST')

    def test_create_team_child_of_must_be_in_same_organization(self):
        organization_1 = self._create_organization(domain='first')
        organization_2 = self._create_organization(domain='second')
        root_team = self._create_team(
            organization_id=organization_1.id,
            name='E-Staff',
        )

        response = self.client.call_action(
            'create_team',
            organization_id=organization_2.id,
            owner_id=uuid.uuid4().hex,
            name='Engineering',
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
            organization_id=organization.id,
            owner_id=uuid.uuid4().hex,
            name='Engineering',
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
            address_id=uuid.uuid4().hex,
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
