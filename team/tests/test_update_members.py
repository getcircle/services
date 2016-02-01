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

    def test_update_members_team_id_required(self):
        with self.assertFieldError('team_id', 'MISSING'):
            self.client.call_action('update_members')

    def test_update_members_team_id_invalid(self):
        members = [{'profile_id': fuzzy.uuid()}]
        with self.assertFieldError('team_id', 'INVALID'):
            self.client.call_action('update_members', team_id='invalid', members=members)

    def test_update_members_members_required(self):
        with self.assertFieldError('members', 'MISSING'):
            self.client.call_action('update_members', team_id=fuzzy.uuid())

    def test_update_members_team_id_does_not_exist(self):
        members = [{'profile_id': fuzzy.uuid()}]
        with self.assertFieldError('team_id', 'DOES_NOT_EXIST'):
            self.client.call_action('update_members', team_id=fuzzy.uuid(), members=members)

    def test_update_members_team_id_wrong_organization(self):
        team = factories.TeamFactory.create_protobuf()
        members = [{'profile_id': fuzzy.uuid()}]
        with self.assertFieldError('team_id', 'DOES_NOT_EXIST'):
            self.client.call_action('update_members', team_id=team.id, members=members)

    def test_update_members_not_member(self):
        team = factories.TeamFactory.create(organization_id=self.organization.id)
        members = factories.TeamMemberFactory.create_protobufs(
            size=2,
            team=team,
            organization_id=self.organization.id,
        )
        with self.assertRaisesCallActionError() as expected:
            self.client.call_action('update_members', team_id=str(team.id), members=members)
        self.assertIn('PERMISSION_DENIED', expected.exception.response.errors)

    def test_update_members_not_coordinator(self):
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
            self.client.call_action('update_members', team_id=str(team.id), members=members)
        self.assertIn('PERMISSION_DENIED', expected.exception.response.errors)

    def test_update_members(self):
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
        for member in members:
            member.role = team_containers.TeamMemberV1.COORDINATOR

        self.client.call_action('update_members', team_id=str(team.id), members=members)
        coordinators = models.TeamMember.objects.filter(
            team_id=team.id,
            role=team_containers.TeamMemberV1.COORDINATOR,
        ).count()
        self.assertEqual(coordinators, 3)
        # ensure we're tracking who updated the role
        calls = [call for call in self.mock.instance.mocked_calls if call['service'] == 'history']
        self.assertEqual(len(calls), 2)
