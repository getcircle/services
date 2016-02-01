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

    def test_remove_members_team_id_required(self):
        with self.assertFieldError('team_id', 'MISSING'):
            self.client.call_action('remove_members')

    def test_remove_members_team_id_invalid(self):
        with self.assertFieldError('team_id', 'INVALID'):
            self.client.call_action(
                'remove_members',
                team_id='invalid',
                profile_ids=[fuzzy.uuid()],
            )

    def test_remove_members_team_id_does_not_exist(self):
        with self.assertFieldError('team_id', 'DOES_NOT_EXIST'):
            self.client.call_action(
                'remove_members',
                team_id=fuzzy.uuid(),
                profile_ids=[fuzzy.uuid()],
            )

    def test_remove_members_wrong_organization(self):
        team = factories.TeamFactory.create_protobuf()
        with self.assertFieldError('team_id', 'DOES_NOT_EXIST'):
            self.client.call_action(
                'remove_members',
                team_id=team.id,
                profile_ids=[fuzzy.uuid()],
            )

    def test_remove_members_profile_ids_required(self):
        with self.assertFieldError('profile_ids', 'MISSING'):
            self.client.call_action('remove_members', team_id=fuzzy.uuid())

    def test_remove_members_profile_ids_invalid(self):
        with self.assertFieldError('profile_ids', 'INVALID'):
            self.client.call_action(
                'remove_members',
                team_id=fuzzy.uuid(),
                profile_ids=['invalid'],
            )

    def test_remove_members_not_member(self):
        team = factories.TeamFactory.create(organization_id=self.organization.id)
        members = factories.TeamMemberFactory.create_protobufs(
            size=2,
            team=team,
            organization_id=self.organization.id,
        )
        with self.assertRaisesCallActionError() as expected:
            self.client.call_action(
                'remove_members',
                team_id=str(team.id), profile_ids=[m.profile_id for m in members],
            )
        self.assertIn('PERMISSION_DENIED', expected.exception.response.errors)

    def test_remove_members_member(self):
        team = factories.TeamFactory.create(organization_id=self.organization.id)
        factories.TeamMemberFactory.create(
            team=team,
            organization_id=self.organization.id,
            profile_id=self.profile.id,
        )
        members = factories.TeamMemberFactory.create_protobufs(
            size=2,
            team=team,
            organization_id=self.organization.id,
        )
        with self.assertRaisesCallActionError() as expected:
            self.client.call_action(
                'remove_members',
                team_id=str(team.id), profile_ids=[m.profile_id for m in members],
            )
        self.assertIn('PERMISSION_DENIED', expected.exception.response.errors)

    def test_remove_members_coordinator(self):
        team = factories.TeamFactory.create(organization_id=self.organization.id)
        factories.TeamMemberFactory.create(
            team=team,
            organization_id=self.organization.id,
            profile_id=self.profile.id,
            role=team_containers.TeamMemberV1.COORDINATOR,
        )
        members = factories.TeamMemberFactory.create_protobufs(
            size=2,
            team=team,
            organization_id=self.organization.id,
        )
        self.client.call_action(
            'remove_members',
            team_id=str(team.id), profile_ids=[m.profile_id for m in members],
        )
        self.assertFalse(models.TeamMember.objects.filter(
            team_id=team.id,
            profile_id__in=[m.profile_id for m in members],
        ).exists())
