import service.control
from services.test import (
    fuzzy,
    mocks,
    MockedTestCase,
)

from .. import (
    factories,
    models,
)


class OrganizationTeamTests(MockedTestCase):

    def setUp(self):
        super(OrganizationTeamTests, self).setUp()
        self.organization = factories.OrganizationFactory.create()
        self.profile = mocks.mock_profile(organization_id=str(self.organization.id))
        self.client = service.control.Client(
            'organization',
            token=mocks.mock_token(
                organization_id=str(self.organization.id),
                profile_id=self.profile.id,
            ),
        )
        self.mock.instance.dont_mock_service('organization')

    def _mock_requester_profile(self, profile_id=None):
        if profile_id is None:
            profile = self.profile
        else:
            profile = mocks.mock_profile(id=profile_id)
        self.mock.instance.register_mock_object(
            'profile',
            'get_profile',
            return_object_path='profile',
            return_object=profile,
            profile_id=profile.id,
            inflations={'disabled': True},
        )
        self.mock.instance.register_mock_object(
            'profile',
            'get_profile',
            return_object_path='profile',
            return_object=profile,
            profile_id=profile.id,
        )

    def test_get_team_invalid_team_id(self):
        with self.assertFieldError('team_id'):
            self.client.call_action('get_team', team_id='invalid')

    def test_get_team_does_not_exist(self):
        with self.assertFieldError('team_id', 'DOES_NOT_EXIST'):
            self.client.call_action('get_team', team_id=fuzzy.FuzzyUUID().fuzz())

    def test_get_team(self):
        team = factories.TeamFactory.create_protobuf(organization=self.organization)
        manager = mocks.mock_profile(id=str(team.manager_profile_id))
        self._mock_requester_profile()
        self.mock.instance.register_mock_object(
            'profile',
            'get_profile',
            return_object_path='profile',
            return_object=manager,
            profile_id=team.manager_profile_id,
        )
        response = self.client.call_action('get_team', team_id=str(team.id))
        self.verify_containers(team, response.result.team)
        self.verify_containers(response.result.team.manager, manager)
        self.assertEqual(response.result.team.profile_count, 2)
        self.assertEqual(response.result.team.child_team_count, 0)

    def test_get_team_with_child_teams(self):
        root = factories.ReportingStructureFactory.create(
            manager_id=None,
            organization_id=self.organization.id,
        )
        middle_manager = factories.ReportingStructureFactory.create(
            manager_id=root.profile_id,
            organization_id=self.organization.id,
        )
        factories.ReportingStructureFactory.create(
            manager_id=middle_manager.profile_id,
            organization_id=self.organization.id,
        )
        team = factories.TeamFactory.create_protobuf(
            organization=self.organization,
            manager_profile_id=root.profile_id,
        )
        child_team = factories.TeamFactory.create_protobuf(
            organization=self.organization,
            manager_profile_id=middle_manager.profile_id,
        )
        self._mock_requester_profile()
        self.mock.instance.register_mock_object(
            'profile',
            'get_profile',
            return_object_path='profile',
            return_object=mocks.mock_profile(id=team.manager_profile_id),
            profile_id=team.manager_profile_id,
        )
        response = self.client.call_action('get_team', team_id=team.id)
        self.verify_containers(team, response.result.team)
        self.assertEqual(response.result.team.profile_count, 3)
        self.assertEqual(response.result.team.child_team_count, 1)

        self.mock.instance.register_mock_object(
            'profile',
            'get_profile',
            return_object_path='profile',
            return_object=mocks.mock_profile(id=child_team.manager_profile_id),
            profile_id=child_team.manager_profile_id,
        )
        response = self.client.call_action('get_team', team_id=child_team.id)
        self.verify_containers(child_team, response.result.team)
        self.assertEqual(response.result.team.profile_count, 2)
        self.assertEqual(response.result.team.child_team_count, 0)

    def test_get_team_include_permissions_not_admin(self):
        team = factories.TeamFactory.create_protobuf(organization=self.organization)
        manager = mocks.mock_profile(id=str(team.manager_profile_id))
        self._mock_requester_profile()
        self.mock.instance.register_mock_object(
            'profile',
            'get_profile',
            return_object_path='profile',
            return_object=manager,
            profile_id=team.manager_profile_id,
        )
        response = self.client.call_action('get_team', team_id=str(team.id))
        team = response.result.team
        self.assertFalse(team.permissions.can_add)
        self.assertFalse(team.permissions.can_edit)
        self.assertFalse(team.permissions.can_delete)

    def test_get_team_include_permissions_admin(self):
        self.profile.is_admin = True
        team = factories.TeamFactory.create_protobuf(organization=self.organization)
        manager = mocks.mock_profile(id=str(team.manager_profile_id))
        self._mock_requester_profile()
        self.mock.instance.register_mock_object(
            'profile',
            'get_profile',
            return_object_path='profile',
            return_object=manager,
            profile_id=team.manager_profile_id,
        )
        response = self.client.call_action('get_team', team_id=str(team.id))
        team = response.result.team
        self.assertTrue(team.permissions.can_add)
        self.assertTrue(team.permissions.can_edit)
        self.assertTrue(team.permissions.can_delete)

    def test_get_team_include_permissions_team_member(self):
        team = factories.TeamFactory.create_protobuf(organization=self.organization)
        manager = mocks.mock_profile(id=str(team.manager_profile_id))
        factories.ReportingStructureFactory.create(
            manager_id=manager.id,
            organization_id=self.organization.id,
            profile_id=self.profile.id,
        )
        self._mock_requester_profile()
        self.mock.instance.register_mock_object(
            'profile',
            'get_profile',
            return_object_path='profile',
            return_object=manager,
            profile_id=team.manager_profile_id,
        )
        response = self.client.call_action('get_team', team_id=str(team.id))
        team = response.result.team
        self.assertFalse(team.permissions.can_add)
        self.assertFalse(team.permissions.can_delete)
        self.assertTrue(team.permissions.can_edit)

    def test_get_team_include_permissions_team_manager(self):
        team = factories.TeamFactory.create_protobuf(
            organization=self.organization,
            manager_profile_id=self.profile.id,
        )
        manager = mocks.mock_profile(id=str(self.profile.id))
        factories.ReportingStructureFactory.create(
            organization_id=self.organization.id,
            profile_id=self.profile.id,
        )
        self._mock_requester_profile()
        self.mock.instance.register_mock_object(
            'profile',
            'get_profile',
            return_object_path='profile',
            return_object=manager,
            profile_id=team.manager_profile_id,
        )
        response = self.client.call_action('get_team', team_id=str(team.id))
        team = response.result.team
        self.assertFalse(team.permissions.can_add)
        self.assertFalse(team.permissions.can_delete)
        self.assertTrue(team.permissions.can_edit)

    def test_update_team_profile_admin(self):
        self.profile.is_admin = True
        team = factories.TeamFactory.create_protobuf(organization=self.organization)
        manager = mocks.mock_profile(id=str(team.manager_profile_id))
        team.name = 'new name'
        team.image_url = 'http://www.newimage.com'
        self._mock_requester_profile()
        self.mock.instance.register_mock_object(
            'profile',
            'get_profile',
            return_object_path='profile',
            return_object=manager,
            profile_id=team.manager_profile_id,
        )
        response = self.client.call_action('update_team', team=team)

        self.assertEqual(response.result.team.name, team.name)
        self.assertTrue(response.result.team.permissions.can_edit)
        self.assertTrue(response.result.team.permissions.can_add)
        self.assertTrue(response.result.team.permissions.can_delete)
        self.assertEqual(response.result.team.image_url, team.image_url)

        instance = models.Team.objects.get(pk=team.id)
        self.assertEqual(instance.name, team.name)

    def test_update_team_profile_non_admin(self):
        self.profile.is_admin = False
        team = factories.TeamFactory.create_protobuf(organization=self.organization)
        team.name = 'new name'
        self._mock_requester_profile()
        with self.assertRaisesCallActionError() as expected:
            self.client.call_action('update_team', team=team)

        self.assertIn('PERMISSION_DENIED', expected.exception.response.errors)

    def test_update_team_profile_non_admin_member(self):
        self.profile.is_admin = False
        team = factories.TeamFactory.create_protobuf(organization=self.organization)
        manager = mocks.mock_profile(id=str(team.manager_profile_id))
        factories.ReportingStructureFactory.create(
            manager_id=manager.id,
            organization_id=self.organization.id,
            profile_id=self.profile.id,
        )
        team.name = 'new name'
        self._mock_requester_profile()
        self.mock.instance.register_mock_object(
            'profile',
            'get_profile',
            return_object_path='profile',
            return_object=manager,
            profile_id=team.manager_profile_id,
        )
        response = self.client.call_action('update_team', team=team)
        # ignore profile_count since we add the user as a member manually
        self.verify_containers(
            team,
            response.result.team,
            ignore_fields=(
                'display_name',
                'profile_count',
            ),
        )

    def test_update_team_non_editable_fields(self):
        self.profile.is_admin = True
        team = factories.TeamFactory.create_protobuf(organization=self.organization)
        manager = mocks.mock_profile(id=str(team.manager_profile_id))
        team.organization_id = fuzzy.FuzzyUUID().fuzz()
        team.manager_profile_id = fuzzy.FuzzyUUID().fuzz()
        team.name = 'new name'
        self._mock_requester_profile()
        self.mock.instance.register_mock_object(
            'profile',
            'get_profile',
            return_object_path='profile',
            return_object=manager,
            profile_id=team.manager_profile_id,
        )
        response = self.client.call_action('update_team', team=team)

        updated_team = response.result.team
        self.assertNotEqual(updated_team.organization_id, team.organization_id)
        self.assertNotEqual(updated_team.manager_profile_id, team.manager_profile_id)
        self.assertEqual(updated_team.name, team.name)

    def _test_update_team(self, team, manager):
        self.mock.instance.register_empty_response(
            service='history',
            action='record_action',
            mock_regex_lookup='history:record_action:.*',
        )
        self._mock_requester_profile()
        self.mock.instance.register_mock_object(
            'profile',
            'get_profile',
            return_object_path='profile',
            return_object=manager,
            profile_id=team.manager_profile_id,
        )
        return self.client.call_action('update_team', team=team)

    def test_update_team_description(self):
        self.profile.is_admin = True
        team = factories.TeamFactory.create_protobuf(organization=self.organization)
        manager = mocks.mock_profile(id=str(team.manager_profile_id))
        team.description.value = 'new description'

        # update the team once
        response = self._test_update_team(team, manager)
        expected_description = team.description
        actual_description = response.result.team.description
        self.assertEqual(actual_description.value, expected_description.value)
        self.assertEqualUUID4(actual_description.by_profile_id, self.profile.id)
        self.assertTrue(actual_description.changed)
        self.verify_containers(self.profile, actual_description.by_profile)

        # update the description again
        team = response.result.team
        team.description.value = 'newer description'
        response = self._test_update_team(team, manager)
        team_description = response.result.team.description
        self.assertEqual(team_description.value, team.description.value)
        self.assertNotEqual(team_description.changed, team.description.changed)

    def test_get_teams(self):
        teams = factories.TeamFactory.create_protobufs(size=3, organization=self.organization)
        team_dict = dict((team.id, team) for team in teams)
        # create teams in other organizations
        factories.TeamFactory.create_batch(size=3)

        response = self.client.call_action('get_teams')
        self.assertEqual(len(response.result.teams), 3)
        for team in response.result.teams:
            self.verify_containers(team_dict.get(team.id), team)

    def test_get_teams_with_ids(self):
        teams = factories.TeamFactory.create_protobufs(size=3, organization=self.organization)
        team_dict = dict((team.id, team) for team in teams)
        # create teams in other organizations
        factories.TeamFactory.create_batch(size=3)

        response = self.client.call_action('get_teams', ids=[str(t.id) for t in teams])
        self.assertEqual(len(response.result.teams), 3)
        for team in response.result.teams:
            self.verify_containers(team_dict.get(team.id), team)
