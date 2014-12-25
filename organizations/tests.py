import uuid
from django.test import TestCase
import service.control


class TestOrganizations(TestCase):

    def setUp(self):
        self.client = service.control.Client(
            'organization',
            token='test-token',
        )
        self.organization_name = 'RH Labs Inc.'
        self.organization_domain = 'rhlabs.com'

    def _verify_error(self, response, code, key, detail):
        self.assertFalse(response.success)
        self.assertIn(code, response.errors)
        error = response.error_details[0]
        self.assertEqual(key, error.key)
        self.assertEqual(detail, error.detail)

    def _verify_field_error(self, response, key, detail='INVALID'):
        self._verify_error(response, 'FIELD_ERROR', key, detail)

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

    def _add_team_member(self, team_id, user_id):
        response = self.client.call_action(
            'add_team_member',
            team_id=team_id,
            user_id=user_id,
        )
        self.assertTrue(response.success)

    def _remove_team_member(self, team_id, user_id):
        response = self.client.call_action(
            'remove_team_member',
            team_id=team_id,
            user_id=user_id,
        )
        self.assertTrue(response.success)

    def _get_team_members(self, team_id):
        # XXX paginate
        response = self.client.call_action(
            'get_team_members',
            team_id=team_id,
        )
        self.assertTrue(response.success)
        return response.result.members

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

    def test_add_team_member_invalid_team_id(self):
        response = self.client.call_action(
            'add_team_member',
            team_id='invalid',
            user_id=uuid.uuid4().hex,
        )
        self._verify_field_error(response, 'team_id')

    def test_add_team_member_invalid_user_id(self):
        response = self.client.call_action(
            'add_team_member',
            team_id=uuid.uuid4().hex,
            user_id='invalid',
        )
        self._verify_field_error(response, 'user_id')

    def test_get_team_members_invalid_team_id(self):
        response = self.client.call_action(
            'get_team_members',
            team_id='invalid',
        )
        self._verify_field_error(response, 'team_id')

    def test_get_team_members_does_not_exist(self):
        response = self.client.call_action(
            'get_team_members',
            team_id=uuid.uuid4().hex,
        )
        self._verify_field_error(response, 'team_id', 'DOES_NOT_EXIST')

    def test_add_team_member(self):
        organization = self._create_organization()
        team = self._create_team(
            organization_id=organization.id,
            name='E-Staff',
        )
        user_id = uuid.uuid4().hex
        self._add_team_member(team.id, user_id)

        members = self._get_team_members(team.id)
        self.assertIn(user_id, members)

    def test_remove_team_member_invalid_team_id(self):
        response = self.client.call_action(
            'remove_team_member',
            team_id='invalid',
            user_id=uuid.uuid4().hex,
        )
        self._verify_field_error(response, 'team_id')

    def test_remove_team_member_team_id_does_not_exist(self):
        response = self.client.call_action(
            'remove_team_member',
            team_id=uuid.uuid4().hex,
            user_id=uuid.uuid4().hex,
        )
        self._verify_field_error(response, 'team_id', 'DOES_NOT_EXIST')

    def test_remove_team_member_invalid_user_id(self):
        team = self._create_team(name='random')
        response = self.client.call_action(
            'remove_team_member',
            team_id=team.id,
            user_id='invalid',
        )
        self._verify_field_error(response, 'user_id')

    def test_remove_team_member(self):
        organization = self._create_organization()
        team = self._create_team(
            organization_id=organization.id,
            name='E-Staff',
        )
        user_id = uuid.uuid4().hex
        self._add_team_member(team.id, user_id)

        team_members = self._get_team_members(team.id)
        self.assertIn(user_id, team_members)

        self._remove_team_member(team.id, user_id)
        team_members = self._get_team_members(team.id)
        self.assertNotIn(user_id, team_members)

    def test_add_team_members_invalid_team_id(self):
        response = self.client.call_action(
            'add_team_members',
            team_id='invalid',
            user_ids=[uuid.uuid4().hex],
        )
        self._verify_field_error(response, 'team_id')

    def test_add_team_members_team_does_not_exist(self):
        response = self.client.call_action(
            'add_team_members',
            team_id=uuid.uuid4().hex,
            user_ids=[uuid.uuid4().hex],
        )
        self._verify_field_error(response, 'team_id', 'DOES_NOT_EXIST')

    def test_add_team_members_invalid_user_ids(self):
        team = self._create_team('random')
        response = self.client.call_action(
            'add_team_members',
            team_id=team.id,
            user_ids=['invalid'],
        )
        self._verify_field_error(response, 'user_ids')

    def test_add_team_members(self):
        # XXX replace this with the fuzzy factory
        team = self._create_team('random')
        user_ids = [uuid.uuid4().hex for _ in range(3)]
        response = self.client.call_action(
            'add_team_members',
            team_id=team.id,
            user_ids=user_ids,
        )
        self.assertTrue(response.success)

        team_members = self._get_team_members(team.id)
        for user_id in user_ids:
            self.assertIn(user_id, team_members)

    def test_remove_team_members_invalid_team_id(self):
        response = self.client.call_action(
            'remove_team_members',
            team_id='invalid',
            user_ids=[uuid.uuid4().hex],
        )
        # TODO make this a context manager
        self._verify_field_error(response, 'team_id')

    def test_remove_team_members_team_does_not_exist(self):
        response = self.client.call_action(
            'remove_team_members',
            team_id=uuid.uuid4().hex,
            user_ids=[uuid.uuid4().hex],
        )
        self._verify_field_error(response, 'team_id', 'DOES_NOT_EXIST')

    def test_remove_team_members_user_ids_invalid(self):
        team = self._create_team('random')
        response = self.client.call_action(
            'remove_team_members',
            team_id=team.id,
            user_ids=['invalid'],
        )
        self._verify_field_error(response, 'user_ids')

    def test_remove_team_members(self):
        team = self._create_team('random')
        user_ids = [uuid.uuid4().hex for _ in range(3)]
        response = self.client.call_action(
            'add_team_members',
            team_id=team.id,
            user_ids=user_ids,
        )
        self.assertTrue(response.success)

        team_members = self._get_team_members(team.id)
        for user_id in user_ids:
            self.assertIn(user_id, team_members)

        response = self.client.call_action(
            'remove_team_members',
            team_id=team.id,
            user_ids=user_ids,
        )
        self.assertTrue(response.success)

        team_members = self._get_team_members(team.id)
        for user_id in user_ids:
            self.assertNotIn(user_id, team_members)

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