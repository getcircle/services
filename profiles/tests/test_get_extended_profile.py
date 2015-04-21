import uuid
from protobufs.services.profile import containers_pb2 as profile_containers
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
        # mock identities for all calls
        self.identities = self._mock_get_identities()
        # mock resume for all calls
        self.resume = self._mock_get_resume()

    def tearDown(self):
        service.settings.DEFAULT_TRANSPORT = 'service.transports.local.instance'

    def _mock_get_location(self, profile, **overrides):
        service = 'organization'
        action = 'get_location'
        mock_response = mock.get_mockable_response(service, action)
        mocks.mock_location(mock_response.location, **overrides)
        location_id = str(uuid.UUID(profile.location_id, version=4))
        mock.instance.register_mock_response(
            service,
            action,
            mock_response,
            location_id=location_id,
        )
        return mock_response.location

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

    def _mock_get_direct_reports(self, profile, count=3, **overrides):
        service = 'profile'
        action = 'get_direct_reports'
        mock_response = mock.get_mockable_response(service, action)
        for _ in range(count):
            container = mock_response.profiles.add()
            mocks.mock_profile(container)

        mock.instance.register_mock_response(
            service,
            action,
            mock_response,
            profile_id=profile.id,
        )
        return mock_response.profiles

    def _mock_get_identities(self, count=3, **overrides):
        service = 'user'
        action = 'get_identities'
        mock_response = mock.get_mockable_response(service, action)
        for _ in range(count):
            container = mock_response.identities.add()
            mocks.mock_identity(container)

        mock.instance.register_mock_response(
            service,
            action,
            mock_response,
            mock_regex_lookup='%s:%s:.*' % (service, action),
        )
        return mock_response.identities

    def _mock_get_resume(self, positions=3, educations=3, **overrides):
        service = 'resume'
        action = 'get_resume'
        mock_response = mock.get_mockable_response(service, action)
        for _ in range(positions):
            container = mock_response.resume.positions.add()
            mocks.mock_position(container)

        for _ in range(educations):
            container = mock_response.resume.educations.add()
            mocks.mock_education(container)

        mock.instance.register_mock_response(
            service,
            action,
            mock_response,
            mock_regex_lookup='%s:%s:.*' % (service, action),
        )
        return mock_response.resume

    def test_get_extended_profile_invalid_profile_id(self):
        with self.assertFieldError('profile_id'):
            self.client.call_action(
                'get_extended_profile',
                profile_id='invalid',
            )

    def test_get_extended_profile_does_not_exist(self):
        with self.assertFieldError('profile_id', 'DOES_NOT_EXIST'):
            self.client.call_action(
                'get_extended_profile',
                profile_id=fuzzy.FuzzyUUID().fuzz(),
            )

    def test_get_extended_profile(self):
        manager = factories.ProfileFactory.create_protobuf()
        skills = factories.TagFactory.create_batch(size=2, type=profile_containers.TagV1.SKILL)
        interests = factories.TagFactory.create_batch(
            size=2,
            type=profile_containers.TagV1.INTEREST,
        )
        profile = factories.ProfileFactory.create_protobuf(tags=skills + interests)
        location = self._mock_get_location(profile)
        team = self._mock_get_team(profile, owner_id=manager.user_id)
        notes = self._mock_get_notes(
            for_profile_id=profile.id,
            owner_profile_id=self.profile_id,
        )
        direct_reports = self._mock_get_direct_reports(profile)

        # fetch the extended profile
        response = self.client.call_action(
            'get_extended_profile',
            profile_id=profile.id,
        )

        self.assertTrue(response.success)
        self._verify_containers(manager, response.result.manager)
        self._verify_containers(location, response.result.location)
        self._verify_containers(team, response.result.team)
        self._verify_containers(profile, response.result.profile)
        self.assertEqual(len(skills), len(response.result.skills))
        self.assertEqual(len(interests), len(response.result.interests))
        self.assertEqual(len(notes), len(response.result.notes))
        self.assertEqual(len(direct_reports), len(response.result.direct_reports))
        self.assertEqual(len(self.identities), len(response.result.identities))
        self._verify_containers(self.resume, response.result.resume)

    def test_get_extended_profile_of_manager(self):
        manager = factories.ProfileFactory.create_protobuf()
        managers_team = self._mock_get_team(
            manager,
            team_id=manager.team_id,
            owner_id=manager.user_id,
            id=manager.team_id,
        )

        profile = factories.ProfileFactory.create_protobuf()
        self._mock_get_location(profile)
        self._mock_get_team(profile, owner_id=profile.user_id, path=[managers_team.path[0]])
        self._mock_get_notes(for_profile_id=profile.id, owner_profile_id=self.profile_id, count=0)
        self._mock_get_direct_reports(profile)

        response = self.client.call_action(
            'get_extended_profile',
            profile_id=profile.id,
        )

        self.assertTrue(response.success)
        self.assertNotEqual(response.result.manager.id, response.result.profile.id)

    def test_get_extended_profile_of_ceo(self):
        profile = factories.ProfileFactory.create_protobuf(id=self.profile_id)
        self._mock_get_team(
            profile,
            owner_id=profile.user_id,
            id=profile.team_id,
        )

        self._mock_get_location(profile)
        self._mock_get_notes(for_profile_id=profile.id, owner_profile_id=self.profile_id, count=0)
        self._mock_get_direct_reports(profile)

        response = self.client.call_action(
            'get_extended_profile',
            profile_id=profile.id,
        )

        self.assertTrue(response.success)
        self.assertFalse(response.result.manager.id)
