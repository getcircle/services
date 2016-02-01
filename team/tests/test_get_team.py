from protobufs.services.common.containers import description_pb2
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

    def test_get_team_team_id_required(self):
        with self.assertFieldError('team_id', 'MISSING'):
            self.client.call_action('get_team')

    def test_get_team_team_id_invalid(self):
        with self.assertFieldError('team_id', 'INVALID'):
            self.client.call_action('get_team', team_id='invalid')

    def test_get_team_wrong_organization(self):
        team = factories.TeamFactory.create()
        with self.assertFieldError('team_id', 'DOES_NOT_EXIST'):
            self.client.call_action('get_team', team_id=str(team.id))

    def test_get_team(self):
        profile = mocks.mock_profile()
        self.mock.instance.register_mock_object(
            service='profile',
            action='get_profile',
            return_object_path='profile',
            return_object=profile,
            profile_id=profile.id,
            inflations={'disabled': True},
        )
        expected = factories.TeamFactory.create_protobuf(
            description=mocks.mock_description(by_profile_id=profile.id),
            organization_id=self.organization.id,
        )
        response = self.client.call_action('get_team', team_id=expected.id)
        self.verify_containers(expected, response.result.team, ignore_fields=('description',))
        description = response.result.team.description
        self.verify_containers(profile, description.by_profile)

    def test_get_team_dont_inflate_profile(self):
        profile = mocks.mock_profile()
        self.mock.instance.register_mock_object(
            service='profile',
            action='get_profile',
            return_object_path='profile',
            return_object=profile,
            profile_id=profile.id,
            inflations={'disabled': True},
        )
        expected = factories.TeamFactory.create_protobuf(
            description=mocks.mock_description(by_profile_id=profile.id),
            organization_id=self.organization.id,
        )
        response = self.client.call_action(
            'get_team',
            team_id=expected.id,
            inflations={'disabled': True},
        )
        self.verify_containers(expected, response.result.team)
        self.assertEqual(response.result.team.description.by_profile.ByteSize(), 0)
