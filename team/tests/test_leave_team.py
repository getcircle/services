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

    def test_leave_team_team_id_required(self):
        with self.assertFieldError('team_id', 'MISSING'):
            self.client.call_action('leave_team')

    def test_leave_team_team_id_invalid(self):
        with self.assertFieldError('team_id', 'INVALID'):
            self.client.call_action('leave_team', team_id='invalid')

    def test_leave_team_team_id_doesn_not_exist(self):
        with self.assertFieldError('team_id', 'DOES_NOT_EXIST'):
            self.client.call_action('leave_team', team_id=fuzzy.uuid())

    def test_leave_team_wrong_organization(self):
        team = factories.TeamFactory.create()
        with self.assertFieldError('team_id', 'DOES_NOT_EXIST'):
            self.client.call_action('leave_team', team_id=str(team.id))

    def test_leave_team(self):
        team = factories.TeamFactory.create(organization_id=self.organization.id)
        factories.TeamMemberFactory.create(
            team=team,
            organization_id=self.organization.id,
            profile_id=self.profile.id,
        )
        self.client.call_action('leave_team', team_id=str(team.id))
        self.assertFalse(models.TeamMember.objects.filter(
            team_id=team.id,
            profile_id=self.profile.id,
        ).exists())

    def test_leave_team_not_member_noop(self):
        team = factories.TeamFactory.create(organization_id=self.organization.id)
        self.client.call_action('leave_team', team_id=str(team.id))

    def test_leave_team_only_coordinator_denied(self):
        team = factories.TeamFactory.create(organization_id=self.organization.id)
        factories.TeamMemberFactory.create(
            team=team,
            organization_id=self.organization.id,
            profile_id=self.profile.id,
            role=team_containers.TeamMemberV1.COORDINATOR,
        )
        with self.assertRaisesCallActionError() as expected:
            self.client.call_action('leave_team', team_id=str(team.id))

        self.assertIn('ONE_COORDINATOR_REQUIRED', expected.exception.response.errors)

    def test_leave_team_multiple_coordinators(self):
        team = factories.TeamFactory.create(organization_id=self.organization.id)
        factories.TeamMemberFactory.create(
            team=team,
            organization_id=self.organization.id,
            profile_id=self.profile.id,
            role=team_containers.TeamMemberV1.COORDINATOR,
        )
        factories.TeamMemberFactory.create(
            team=team,
            organization_id=self.organization.id,
            role=team_containers.TeamMemberV1.COORDINATOR,
        )
        self.client.call_action('leave_team', team_id=str(team.id))
        self.assertFalse(models.TeamMember.objects.filter(
            team_id=team.id,
            profile_id=self.profile.id,
        ).exists())
