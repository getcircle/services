from protobufs.services.common import containers_pb2 as common_containers
from protobufs.services.team import containers_pb2 as team_containers
import service.control

from services.test import (
    fuzzy,
    mocks,
    MockedTestCase,
)

from .. import factories


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

    def test_get_teams_wrong_organization(self):
        factories.TeamFactory.create_batch(size=5, organization_id=fuzzy.uuid())
        response = self.client.call_action('get_teams')
        self.assertEqual(len(response.result.teams), 0)

    def test_get_teams(self):
        expected = factories.TeamFactory.create_batch(size=5, organization_id=self.organization.id)
        response = self.client.call_action('get_teams')
        self.assertEqual(len(response.result.teams), len(expected))

    def test_get_teams_by_ids(self):
        fetched = factories.TeamFactory.create_batch(size=2, organization_id=self.organization.id)
        factories.TeamFactory.create_batch(size=3, organization_id=self.organization.id)
        response = self.client.call_action('get_teams', ids=[str(t.id) for t in fetched])
        self.assertEqual(len(response.result.teams), len(fetched))

        fetched_ids = [t.id for t in response.result.teams]
        for team in fetched:
            self.assertIn(str(team.id), fetched_ids)

    def test_get_teams_by_ids_invalid_values(self):
        with self.assertFieldError('ids'):
            self.client.call_action('get_teams', ids=['invalid', 'invalid'])

    def test_get_teams_permissions(self):
        tests = {}

        # user is a member of one team
        team = factories.TeamFactory.create(organization_id=self.organization.id)
        factories.TeamMemberFactory.create(
            team=team,
            organization_id=self.organization.id,
            profile_id=self.profile.id,
        )
        tests[str(team.id)] = common_containers.PermissionsV1(can_add=True)

        # user is a coordinator of a team
        team = factories.TeamFactory.create(organization_id=self.organization.id)
        factories.TeamMemberFactory.create(
            team=team,
            organization_id=self.organization.id,
            profile_id=self.profile.id,
            role=team_containers.TeamMemberV1.COORDINATOR,
        )
        tests[str(team.id)] = common_containers.PermissionsV1(
            can_add=True,
            can_edit=True,
            can_delete=True,
        )

        # user is not a member
        team = factories.TeamFactory.create(organization_id=self.organization.id)
        factories.TeamMemberFactory.create(
            team=team,
            organization_id=self.organization.id,
        )
        tests[str(team.id)] = common_containers.PermissionsV1()

        response = self.client.call_action(
            'get_teams',
            ids=tests.keys(),
            inflations={'only': ['permissions']},
        )
        for team in response.result.teams:
            expected_permissions = tests[team.id]
            self.verify_containers(expected_permissions, team.permissions)

    def test_get_teams_permissions_admin(self):
        self.profile.is_admin = True
        self.mock.instance.register_mock_object(
            service='profile',
            action='get_profile',
            return_object_path='profile',
            return_object=self.profile,
            profile_id=self.profile.id,
            inflations={'disabled': True},
            fields={'only': ['is_admin']},
        )

        team_ids = []
        # user is a member of one team
        team = factories.TeamFactory.create(organization_id=self.organization.id)
        factories.TeamMemberFactory.create(
            team=team,
            organization_id=self.organization.id,
            profile_id=self.profile.id,
        )
        team_ids.append(str(team.id))

        # user is a coordinator of a team
        team = factories.TeamFactory.create(organization_id=self.organization.id)
        factories.TeamMemberFactory.create(
            team=team,
            organization_id=self.organization.id,
            profile_id=self.profile.id,
            role=team_containers.TeamMemberV1.COORDINATOR,
        )
        team_ids.append(str(team.id))

        # user is not a member
        team = factories.TeamFactory.create(organization_id=self.organization.id)
        factories.TeamMemberFactory.create(
            team=team,
            organization_id=self.organization.id,
        )
        team_ids.append(str(team.id))

        response = self.client.call_action(
            'get_teams',
            ids=team_ids,
            inflations={'only': ['permissions']},
        )
        for team in response.result.teams:
            expected_permissions = common_containers.PermissionsV1(
                can_add=True,
                can_edit=True,
                can_delete=True,
            )
            self.verify_containers(expected_permissions, team.permissions)
