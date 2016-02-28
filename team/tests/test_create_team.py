from protobufs.services.history import containers_pb2 as history_containers
from protobufs.services.team import containers_pb2 as team_containers
import service.control

from services.test import (
    fuzzy,
    mocks,
    MockedTestCase,
)

from .. import models


class Test(MockedTestCase):

    def setUp(self):
        super(Test, self).setUp()
        self.organization = mocks.mock_organization()
        self.profile = mocks.mock_profile(organization_id=self.organization.id)
        self.token = mocks.mock_token(
            organization_id=self.organization.id,
            profile_id=self.profile.id,
        )
        self.client = service.control.Client('team', token=self.token)
        self.mock.instance.dont_mock_service('team')

    def test_create_team_team_required(self):
        with self.assertFieldError('team', 'MISSING'):
            self.client.call_action('create_team')

    def test_create_team_team_name_required(self):
        container = team_containers.TeamV1(description=mocks.mock_description())
        with self.assertFieldError('team.name', 'MISSING'):
            self.client.call_action('create_team', team=container)

    def test_create_team(self):
        container = team_containers.TeamV1(
            name=fuzzy.text(),
            description=mocks.mock_description(),
        )
        response = self.client.call_action('create_team', team=container)
        team = response.result.team
        self.verify_containers(container, team, ignore_fields=('description',))
        # verify the permissions are returned
        self.assertTrue(team.permissions.can_edit)
        self.assertTrue(team.permissions.can_add)
        self.assertTrue(team.permissions.can_delete)

        # verify the description by_profile_id is equal to the current users token
        self.assertEqual(team.description.by_profile_id, self.profile.id)
        self.assertEqual(team.organization_id, self.organization.id)
        # verify history action was called
        call = self.mock.instance.mocked_calls[1]
        self.assertEqual(call['action'], 'record_action')
        self.assertEqual(call['service'], 'history')
        params = call['params']
        self.assertEqual(params['action']['table_name'], 'team_team')
        self.assertEqual(params['action']['method_type'], history_containers.CREATE)
        self.assertEqual(params['action']['action_type'], history_containers.CREATE_INSTANCE)

        # verify the user who created the team was added as a coordinator
        coordinator = models.TeamMember.objects.get(team_id=team.id, profile_id=self.profile.id)
        self.assertEqual(coordinator.role, team_containers.TeamMemberV1.COORDINATOR)

    def test_create_team_add_members(self):
        container = team_containers.TeamV1(
            name=fuzzy.text(),
            description=mocks.mock_description(),
        )
        members = [team_containers.TeamMemberV1(profile_id=fuzzy.uuid()) for _ in range(3)]
        response = self.client.call_action('create_team', team=container, members=members)
        team = response.result.team
        self.verify_containers(container, team, ignore_fields=('description'))

        # verify the user who created the team was added as a coordinator
        coordinator = models.TeamMember.objects.get(team_id=team.id, profile_id=self.profile.id)
        self.assertEqual(coordinator.role, team_containers.TeamMemberV1.COORDINATOR)

        # verify we added other users as members
        members = models.TeamMember.objects.filter(team_id=team.id).exclude(
            profile_id=self.profile.id,
        )
        self.assertEqual(len(members), 3)
