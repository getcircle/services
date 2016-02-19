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

    def test_add_members_team_id_required(self):
        with self.assertFieldError('team_id', 'MISSING'):
            self.client.call_action('add_members')

    def test_add_members_members_required(self):
        with self.assertFieldError('members', 'MISSING'):
            self.client.call_action('add_members', team_id=fuzzy.uuid())

    def test_add_members_team_id_does_not_exist(self):
        with self.assertFieldError('team_id', 'DOES_NOT_EXIST'):
            self.client.call_action(
                'add_members',
                team_id=fuzzy.uuid(),
                members=[{'profile_id': fuzzy.uuid()}],
            )

    def test_add_members_team_id_invalid(self):
        with self.assertFieldError('team_id', 'INVALID'):
            self.client.call_action(
                'add_members',
                team_id='invalid',
                members=[{'profile_id': fuzzy.uuid()}],
            )

    def test_add_members(self):
        team = factories.TeamFactory.create(organization_id=self.organization.id)
        members = [{'profile_id': fuzzy.uuid(), 'role': team_containers.TeamMemberV1.COORDINATOR}
                   for _ in range(3)]
        for _ in range(3):
            members.append({
                'profile_id': fuzzy.uuid(),
                'role': team_containers.TeamMemberV1.MEMBER,
            })

        profile_id_to_member = dict((m['profile_id'], m) for m in members)

        response = self.client.call_action('add_members', team_id=str(team.id), members=members)
        self.assertEqual(len(response.result.members), len(members))
        for member in response.result.members:
            self.assertEqual(member.inflations.only, ['profile'])
            expected_member = profile_id_to_member[member.profile_id]
            self.assertEqual(expected_member['role'], member.role)

        coordinators = models.TeamMember.objects.filter(
            team_id=team.id,
            role=team_containers.TeamMemberV1.COORDINATOR,
        )
        self.assertEqual(len(coordinators), 3)
        members = models.TeamMember.objects.filter(
            team_id=team.id,
            role=team_containers.TeamMemberV1.MEMBER,
        )
        self.assertEqual(len(members), 3)

    def test_add_members_duplicate(self):
        team = factories.TeamFactory.create(organization_id=self.organization.id)
        members = [{'profile_id': fuzzy.uuid()}]
        self.client.call_action('add_members', team_id=str(team.id), members=members)
        self.client.call_action('add_members', team_id=str(team.id), members=members)

        # changing the role should still do nothing
        members[0]['role'] = team_containers.TeamMemberV1.COORDINATOR
        response = self.client.call_action('add_members', team_id=str(team.id), members=members)
        self.assertEqual(len(response.result.members), len(members))

        members = models.TeamMember.objects.filter(team_id=team.id)
        self.assertEqual(len(members), 1)
        self.assertEqual(members[0].role, team_containers.TeamMemberV1.MEMBER)

    def test_add_members_dedupe_duplicate_members(self):
        team = factories.TeamFactory.create(organization_id=self.organization.id)
        profile_id = fuzzy.uuid()
        members = [{'profile_id': profile_id}, {'profile_id': profile_id}]
        response = self.client.call_action('add_members', team_id=str(team.id), members=members)
        self.assertEqual(len(response.result.members), 1)

        members = models.TeamMember.objects.filter(team_id=team.id)
        self.assertEqual(len(members), 1)
        self.assertEqual(members[0].role, team_containers.TeamMemberV1.MEMBER)
