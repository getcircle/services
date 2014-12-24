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

    def _verify_error(self, action_response, code, key, detail):
        self.assertFalse(action_response.result.success)
        self.assertIn(code, action_response.result.errors)
        error = action_response.result.error_details[0]
        self.assertEqual(key, error.key)
        self.assertEqual(detail, error.detail)

    def _verify_field_error(self, action_response, key, detail='INVALID'):
        self._verify_error(action_response, 'FIELD_ERROR', key, detail)

    def _create_organization(self, name=None, domain=None):
        action_response, result = self.client.call_action(
            'create_organization',
            name=name or self.organization_name,
            domain=domain or self.organization_domain,
        )
        self.assertTrue(action_response.result.success)
        return result.organization

    def _create_team(
            self,
            name,
            organization_id=None,
            owner_id=None,
            child_of=None,
        ):
        if organization_id is None:
            organization_id = self._create_organization().id

        action_response, result = self.client.call_action(
            'create_team',
            organization_id=organization_id,
            owner_id=owner_id or uuid.uuid4().hex,
            name=name,
            child_of=child_of,
        )
        self.assertTrue(action_response.result.success)
        return result.team

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
        action_response, _ = self.client.call_action(
            'add_team_member',
            team_id=team_id,
            user_id=user_id,
        )
        self.assertTrue(action_response.result.success)

    def _remove_team_member(self, team_id, user_id):
        action_response, _ = self.client.call_action(
            'remove_team_member',
            team_id=team_id,
            user_id=user_id,
        )
        self.assertTrue(action_response.result.success)

    def _get_team_members(self, team_id):
        # XXX paginate
        action_response, result = self.client.call_action(
            'get_team_members',
            team_id=team_id,
        )
        self.assertTrue(action_response.result.success)
        return result.members

    def test_create_organization(self):
        action_response, result = self.client.call_action(
            'create_organization',
            name=self.organization_name,
            domain=self.organization_domain,
        )
        self.assertTrue(action_response.result.success)
        self.assertTrue(uuid.UUID(result.organization.id, version=4))
        self.assertEqual(result.organization.name, self.organization_name)
        self.assertEqual(result.organization.domain, self.organization_domain)

    def test_create_organization_duplicate_domain(self):
        action_response, _ = self.client.call_action(
            'create_organization',
            name=self.organization_name,
            domain=self.organization_domain,
        )
        self.assertTrue(action_response.result.success)

        action_response, _ = self.client.call_action(
            'create_organization',
            name=self.organization_name,
            domain=self.organization_domain,
        )
        self._verify_field_error(action_response, 'domain', 'DUPLICATE')

    def test_create_team_invalid_owner_id(self):
        organization = self._create_organization()
        action_response, _ = self.client.call_action(
            'create_team',
            organization_id=organization.id,
            owner_id='invalid',
            name='E-Staff',
        )
        self._verify_field_error(action_response, 'owner_id')

    def test_create_team_invalid_organization_id(self):
        action_response, _ = self.client.call_action(
            'create_team',
            organization_id='invalid',
            owner_id=uuid.uuid4().hex,
            name='E-Staff',
        )
        self._verify_field_error(action_response, 'organization_id')

    def test_create_team_non_existant_organization(self):
        action_response, _ = self.client.call_action(
            'create_team',
            organization_id=uuid.uuid4().hex,
            owner_id=uuid.uuid4().hex,
            name='E-Staff',
        )
        self._verify_field_error(
            action_response,
            'organization_id',
            'DOES_NOT_EXIST',
        )

    def test_create_team_null_child_of_means_root(self):
        owner_id = uuid.uuid4().hex
        organization = self._create_organization()
        action_response, result = self.client.call_action(
            'create_team',
            organization_id=organization.id,
            owner_id=owner_id,
            name='E-Staff'
        )
        self.assertTrue(action_response.result.success)

        self.assertTrue(uuid.UUID(result.team.id, version=4))
        self.assertEqual(result.team.organization_id, organization.id)
        self.assertEqual(result.team.name, 'E-Staff')
        self.assertEqual(result.team.owner_id, owner_id)
        self.assertEqual(result.team.path, ['E-Staff'])

    def test_create_team_invalid_child_of(self):
        organization = self._create_organization()
        action_response, _ = self.client.call_action(
            'create_team',
            organization_id=organization.id,
            owner_id=uuid.uuid4().hex,
            name='Engineering',
            child_of='invalid',
        )
        self._verify_field_error(action_response, 'child_of')

    def test_create_team_non_existant_child_of(self):
        organization = self._create_organization()
        action_response, _ = self.client.call_action(
            'create_team',
            organization_id=organization.id,
            owner_id=uuid.uuid4().hex,
            name='Engineering',
            child_of=uuid.uuid4().hex,
        )
        self._verify_field_error(action_response, 'child_of', 'DOES_NOT_EXIST')

    def test_create_team_child_of_must_be_in_same_organization(self):
        organization_1 = self._create_organization(domain='first')
        organization_2 = self._create_organization(domain='second')
        root_team = self._create_team(
            organization_id=organization_1.id,
            name='E-Staff',
        )

        action_response, _ = self.client.call_action(
            'create_team',
            organization_id=organization_2.id,
            owner_id=uuid.uuid4().hex,
            name='Engineering',
            child_of=root_team.id,
        )
        self._verify_field_error(action_response, 'child_of', 'DOES_NOT_EXIST')

    def test_create_team_child_of_one_level(self):
        organization = self._create_organization()
        root_team = self._create_team(
            organization_id=organization.id,
            name='E-Staff',
        )

        action_response, result = self.client.call_action(
            'create_team',
            organization_id=organization.id,
            owner_id=uuid.uuid4().hex,
            name='Engineering',
            child_of=root_team.id,
        )
        self.assertTrue(action_response.result.success)
        self.assertEqual(result.team.organization_id, organization.id)
        self.assertEqual(result.team.name, 'Engineering')
        self.assertEqual(result.team.path, ['E-Staff', 'Engineering'])

    def test_create_team_child_of_multiple_levels(self):
        organization = self._create_organization()
        teams = self._create_team_tree(
            organization_id=organization.id,
            levels=4,
        )
        self.assertEqual(len(teams[-1].path), 5)

    def test_add_team_member_invalid_team_id(self):
        action_response, _ = self.client.call_action(
            'add_team_member',
            team_id='invalid',
            user_id=uuid.uuid4().hex,
        )
        self._verify_field_error(action_response, 'team_id')

    def test_add_team_member_invalid_user_id(self):
        action_response, _ = self.client.call_action(
            'add_team_member',
            team_id=uuid.uuid4().hex,
            user_id='invalid',
        )
        self._verify_field_error(action_response, 'user_id')

    def test_get_team_members_invalid_team_id(self):
        action_response, _ = self.client.call_action(
            'get_team_members',
            team_id='invalid',
        )
        self._verify_field_error(action_response, 'team_id')

    def test_get_team_members_does_not_exist(self):
        action_response, _ = self.client.call_action(
            'get_team_members',
            team_id=uuid.uuid4().hex,
        )
        self._verify_field_error(action_response, 'team_id', 'DOES_NOT_EXIST')

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
        action_response, _ = self.client.call_action(
            'remove_team_member',
            team_id='invalid',
            user_id=uuid.uuid4().hex,
        )
        self._verify_field_error(action_response, 'team_id')

    def test_remove_team_member_team_id_does_not_exist(self):
        action_response, _ = self.client.call_action(
            'remove_team_member',
            team_id=uuid.uuid4().hex,
            user_id=uuid.uuid4().hex,
        )
        self._verify_field_error(action_response, 'team_id', 'DOES_NOT_EXIST')

    def test_remove_team_member_invalid_user_id(self):
        team = self._create_team(name='random')
        action_response, _ = self.client.call_action(
            'remove_team_member',
            team_id=team.id,
            user_id='invalid',
        )
        self._verify_field_error(action_response, 'user_id')

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
        action_response, _ = self.client.call_action(
            'add_team_members',
            team_id='invalid',
            user_ids=[uuid.uuid4().hex],
        )
        self._verify_field_error(action_response, 'team_id')

    def test_add_team_members_team_does_not_exist(self):
        action_response, _ = self.client.call_action(
            'add_team_members',
            team_id=uuid.uuid4().hex,
            user_ids=[uuid.uuid4().hex],
        )
        self._verify_field_error(action_response, 'team_id', 'DOES_NOT_EXIST')

    def test_add_team_members_invalid_user_ids(self):
        team = self._create_team('random')
        action_response, _ = self.client.call_action(
            'add_team_members',
            team_id=team.id,
            user_ids=['invalid'],
        )
        self._verify_field_error(action_response, 'user_ids')

    def test_add_team_members(self):
        # XXX replace this with the fuzzy factory
        team = self._create_team('random')
        user_ids = [uuid.uuid4().hex for _ in range(3)]
        action_response, _ = self.client.call_action(
            'add_team_members',
            team_id=team.id,
            user_ids=user_ids,
        )
        self.assertTrue(action_response.result.success)

        team_members = self._get_team_members(team.id)
        for user_id in user_ids:
            self.assertIn(user_id, team_members)

    def test_remove_team_members_invalid_team_id(self):
        action_response, _ = self.client.call_action(
            'remove_team_members',
            team_id='invalid',
            user_ids=[uuid.uuid4().hex],
        )
        # TODO make this a context manager
        self._verify_field_error(action_response, 'team_id')

    def test_remove_team_members_team_does_not_exist(self):
        action_response, _ = self.client.call_action(
            'remove_team_members',
            team_id=uuid.uuid4().hex,
            user_ids=[uuid.uuid4().hex],
        )
        self._verify_field_error(action_response, 'team_id', 'DOES_NOT_EXIST')

    def test_remove_team_members_user_ids_invalid(self):
        team = self._create_team('random')
        action_response, _ = self.client.call_action(
            'remove_team_members',
            team_id=team.id,
            user_ids=['invalid'],
        )
        self._verify_field_error(action_response, 'user_ids')

    def test_remove_team_members(self):
        team = self._create_team('random')
        user_ids = [uuid.uuid4().hex for _ in range(3)]
        action_response, _ = self.client.call_action(
            'add_team_members',
            team_id=team.id,
            user_ids=user_ids,
        )
        self.assertTrue(action_response.result.success)

        team_members = self._get_team_members(team.id)
        for user_id in user_ids:
            self.assertIn(user_id, team_members)

        action_response, _ = self.client.call_action(
            'remove_team_members',
            team_id=team.id,
            user_ids=user_ids,
        )
        self.assertTrue(action_response.result.success)

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
