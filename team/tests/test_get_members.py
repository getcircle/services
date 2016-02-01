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
