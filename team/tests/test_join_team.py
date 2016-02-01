from protobufs.services.team import containers_pb2 as team_containers
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

    def test_join_team_team_id_required(self):
        with self.assertFieldError('team_id', 'MISSING'):
            self.client.call_action('join_team')

    def test_join_team_team_id_invalid(self):
        with self.assertFieldError('team_id', 'INVALID'):
            self.client.call_action('join_team', team_id='invalid')

    def test_join_team_team_id_doesn_not_exist(self):
        with self.assertFieldError('team_id', 'DOES_NOT_EXIST'):
            self.client.call_action('join_team', team_id=fuzzy.uuid())

    def test_join_team_wrong_organization(self):
        team = factories.TeamFactory.create()
        with self.assertFieldError('team_id', 'DOES_NOT_EXIST'):
            self.client.call_action('join_team', team_id=str(team.id))

    def test_join_team(self):
        team = factories.TeamFactory.create_protobuf(organization_id=self.organization.id)
        self.client.call_action('join_team', team_id=team.id)
        membership = models.TeamMember.objects.get(team_id=team.id, profile_id=self.profile.id)
        self.assertEqual(membership.role, team_containers.TeamMemberV1.MEMBER)

    def test_join_team_duplicate_noop(self):
        team = factories.TeamFactory.create(organization_id=self.organization.id)
        factories.TeamMemberFactory.create(
            team=team,
            organization_id=self.organization.id,
            profile_id=self.profile.id,
        )
        self.client.call_action('join_team', team_id=str(team.id))
