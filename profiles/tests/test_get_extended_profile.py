import service.control
import service.settings
from service.transports import (
    local,
    mock,
)
from services.test import (
    fuzzy,
    mocks,
    TestCase,
)

from .. import factories


class TestGetExtendedProfile(TestCase):

    def setUp(self):
        super(TestGetExtendedProfile, self).setUp()
        service.settings.DEFAULT_TRANSPORT = 'service.transports.mock.instance'
        self.client = service.control.Client('profile', token='test-token')
        self.client.set_transport(local.instance)

    def tearDown(self):
        service.settings.DEFAULT_TRANSPORT = 'service.transports.local.instance'

    def _mock_get_address(self, profile, **overrides):
        service = 'organization'
        action = 'get_address'
        mock_response = mock.get_mockable_response(service, action)
        mocks.mock_address(mock_response.address, **overrides)
        mock.instance.register_mock_response(
            service,
            action,
            mock_response,
            address_id=profile.address_id,
        )
        return mock_response.address

    def _mock_get_team(self, profile, **overrides):
        service = 'organization'
        action = 'get_team'
        mock_response = mock.get_mockable_response(service, action)
        mocks.mock_team(mock_response.team, **overrides)
        mock.instance.register_mock_response(
            service,
            action,
            mock_response,
            team_id=profile.team_id,
        )
        return mock_response.team

    def test_get_extended_profile_invalid_profile_id(self):
        response = self.client.call_action(
            'get_extended_profile',
            profile_id='invalid',
        )
        self._verify_field_error(response, 'profile_id')

    def test_get_extended_profile_does_not_exist(self):
        response = self.client.call_action(
            'get_extended_profile',
            profile_id=fuzzy.FuzzyUUID().fuzz(),
        )
        self._verify_field_error(response, 'profile_id', 'DOES_NOT_EXIST')

    def test_get_extended_profile(self):
        manager = factories.ProfileFactory.create_protobuf()
        tags = factories.TagFactory.create_batch(size=2)
        profile = factories.ProfileFactory.create_protobuf(tags=tags)
        address = self._mock_get_address(profile)
        team = self._mock_get_team(profile, owner_id=manager.user_id)

        # fetch the extended profile
        response = self.client.call_action(
            'get_extended_profile',
            profile_id=profile.id,
        )

        self.assertTrue(response.success)
        self._verify_containers(manager, response.result.manager)
        self._verify_containers(address, response.result.address)
        self._verify_containers(team, response.result.team)
        self._verify_containers(profile, response.result.profile)
        self.assertEqual(len(tags), len(response.result.tags))
