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

    def test_get_members_team_id_required(self):
        with self.assertFieldError('team_id', 'MISSING'):
            self.client.call_action('get_members')

    def test_get_members_invalid_team_id(self):
        with self.assertFieldError('team_id', 'INVALID'):
            self.client.call_action('get_members', team_id='invalid')

    def test_get_members_team_id_does_not_exist(self):
        with self.assertFieldError('team_id', 'DOES_NOT_EXIST'):
            self.client.call_action('get_members', team_id=fuzzy.uuid())

    def test_get_members_wrong_organization(self):
        team = factories.TeamFactory.create()
        factories.TeamMemberFactory.create_batch(
            size=2,
            team=team,
            organization_id=team.organization_id,
        )
        with self.assertFieldError('team_id', 'DOES_NOT_EXIST'):
            self.client.call_action('get_members', team_id=str(team.id))

    def test_get_members_no_members_no_get_profiles_call(self):
        team = factories.TeamFactory.create(organization_id=self.organization.id)
        response = self.client.call_action('get_members', team_id=str(team.id))
        self.assertFalse(response.result.members)
        self.assertFalse(self.mock.instance.mocked_calls)

    def test_get_members(self):
        team = factories.TeamFactory.create(organization_id=self.organization.id)
        members = factories.TeamMemberFactory.create_batch(
            size=3,
            organization_id=team.organization_id,
            team=team,
            role=team_containers.TeamMemberV1.MEMBER,
        )
        coordinators = factories.TeamMemberFactory.create_batch(
            size=3,
            organization_id=team.organization_id,
            team=team,
            role=team_containers.TeamMemberV1.COORDINATOR,
        )
        # by default we just return members
        self.mock.instance.register_mock_object(
            service='profile',
            action='get_profiles',
            return_object_path='profiles',
            return_object=[mocks.mock_profile(id=str(m.profile_id)) for m in members],
            mock_regex_lookup='profile:get_profiles.*',
        )
        response = self.client.call_action('get_members', team_id=str(team.id))
        self.assertEqual(len(response.result.members), len(members))
        for member in response.result.members:
            self.assertEqual(member.role, team_containers.TeamMemberV1.MEMBER)
            self.assertTrue(member.profile.ByteSize())

        # can request coordinators
        self.mock.instance.register_mock_object(
            service='profile',
            action='get_profiles',
            return_object_path='profiles',
            return_object=[mocks.mock_profile(id=str(c.profile_id)) for c in coordinators],
            mock_regex_lookup='profile:get_profiles.*',
        )
        response = self.client.call_action(
            'get_members',
            team_id=str(team.id),
            role=team_containers.TeamMemberV1.COORDINATOR,
        )
        self.assertEqual(len(response.result.members), len(coordinators))
        for member in response.result.members:
            self.assertEqual(member.role, team_containers.TeamMemberV1.COORDINATOR)
            self.assertTrue(member.profile.ByteSize())

    def test_get_members_profile_id_invalid(self):
        with self.assertFieldError('profile_id'):
            self.client.call_action('get_members', profile_id='invalid')

    def test_get_members_profile_id_wrong_organization(self):
        profile = mocks.mock_profile()
        factories.TeamMemberFactory.create_protobufs(size=2, profile=profile)
        response = self.client.call_action('get_members', profile_id=profile.id)
        self.assertEqual(len(response.result.members), 0)

    def test_get_members_profile_id(self):
        coordinator_members = factories.TeamMemberFactory.create_protobufs(
            size=2,
            profile=self.profile,
            role=team_containers.TeamMemberV1.COORDINATOR,
        )
        members = factories.TeamMemberFactory.create_protobufs(
            size=2,
            profile=self.profile,
            role=team_containers.TeamMemberV1.MEMBER,
        )
        team_id_to_team = dict(
            (member.team.id, member.team) for member in coordinator_members + members
        )
        response = self.client.call_action('get_members', profile_id=self.profile.id)
        result_members = response.result.members
        self.assertEqual(len(result_members), 4)
        self.assertTrue(
            all([m.role == team_containers.TeamMemberV1.COORDINATOR for m in result_members[:2]]),
            'Coordinator members should be the first returned',
        )
        self.assertTrue(
            all([m.role == team_containers.TeamMemberV1.MEMBER for m in result_members[2:]]),
            'Members should be last returned',
        )

        # verify we inflate the team
        for member in result_members:
            self.assertTrue(member.team.id)
            team = team_id_to_team[member.team.id]
            self.verify_containers(team, member.team)

    def test_get_members_profile_id_inflations(self):
        members = factories.TeamMemberFactory.create_batch(
            size=2,
            profile=self.profile,
            team__description=mocks.mock_description(),
            team__organization_id=self.profile.organization_id,
        )
        for member in members:
            # create some additional members of the team to verify total_members count
            factories.TeamMemberFactory.create_batch(size=4, team=member.team)

        response = self.client.call_action(
            'get_members',
            profile_id=self.profile.id,
            inflations={'only': ['[]members.team', '[]members.team.total_members']},
            fields={'exclude': ['[]members.team.description']},
        )

        for member in response.result.members:
            self.assertIn('team.description', member.fields.exclude)
            self.assertIn('team', member.inflations.only)
            self.assertIn('team.total_members', member.inflations.only)
            self.assertTrue(member.team.id)
            self.assertTrue(member.team.name)
            self.assertEqual(member.team.total_members, 5)
            self.assertFalse(member.team.description.value)
            self.assertFalse(member.team.description.by_profile_id)
