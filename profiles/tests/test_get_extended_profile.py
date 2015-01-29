import uuid
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
        self.profile_id = fuzzy.FuzzyUUID().fuzz()
        self.token = mocks.mock_token(profile_id=self.profile_id)
        self.client = service.control.Client('profile', token=self.token)
        self.client.set_transport(local.instance)

    def tearDown(self):
        service.settings.DEFAULT_TRANSPORT = 'service.transports.local.instance'

    def _mock_get_address(self, profile, **overrides):
        service = 'organization'
        action = 'get_address'
        mock_response = mock.get_mockable_response(service, action)
        mocks.mock_address(mock_response.address, **overrides)
        address_id = str(uuid.UUID(profile.address_id, version=4))
        mock.instance.register_mock_response(
            service,
            action,
            mock_response,
            address_id=address_id,
        )
        return mock_response.address

    def _mock_get_team(self, profile, team_id=None, **overrides):
        service = 'organization'
        action = 'get_team'
        mock_response = mock.get_mockable_response(service, action)
        mocks.mock_team(mock_response.team, **overrides)
        if not team_id:
            team_id = str(uuid.UUID(profile.team_id, version=4))
        mock.instance.register_mock_response(
            service,
            action,
            mock_response,
            team_id=team_id,
        )
        return mock_response.team

    def _mock_get_notes(self, for_profile_id, owner_profile_id, count=2, **overrides):
        service = 'note'
        action = 'get_notes'
        mock_response = mock.get_mockable_response(service, action)
        for _ in range(count):
            container = mock_response.notes.add()
            mocks.mock_note(
                container,
                for_profile_id=for_profile_id,
                owner_profile_id=owner_profile_id,
            )

        mock.instance.register_mock_response(
            service,
            action,
            mock_response,
            for_profile_id=for_profile_id,
            owner_profile_id=owner_profile_id,
        )
        return mock_response.notes

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
        notes = self._mock_get_notes(
            for_profile_id=profile.id,
            owner_profile_id=self.profile_id,
        )

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
        self.assertEqual(len(notes), len(response.result.notes))

    def test_get_extended_profile_of_manager(self):
        manager = factories.ProfileFactory.create_protobuf()
        managers_team = self._mock_get_team(
            manager,
            team_id=manager.team_id,
            owner_id=manager.user_id,
            id=manager.team_id,
        )

        profile = factories.ProfileFactory.create_protobuf()
        self._mock_get_address(profile)
        self._mock_get_team(profile, owner_id=profile.user_id, path=[managers_team.path[0]])
        self._mock_get_notes(for_profile_id=profile.id, owner_profile_id=self.profile_id, count=0)

        response = self.client.call_action(
            'get_extended_profile',
            profile_id=profile.id,
        )

        self.assertTrue(response.success)
        self.assertNotEqual(response.result.manager.id, response.result.profile.id)
