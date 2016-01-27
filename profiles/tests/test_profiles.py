from protobufs.services.profile import containers_pb2 as profile_containers
import service.control
from service_protobufs import soa_pb2

from services.test import (
    fuzzy,
    mocks,
    MockedTestCase,
)

from .. import factories


class TestProfiles(MockedTestCase):

    def setUp(self):
        super(TestProfiles, self).setUp()
        self.organization = mocks.mock_organization()
        self._mock_display_title()
        self.profile = factories.ProfileFactory.create_protobuf(
            organization_id=self.organization.id,
        )
        token = mocks.mock_token(
            profile_id=self.profile.id,
            organization_id=self.organization.id,
        )
        self.client = service.control.Client('profile', token=token)
        self.mock.instance.dont_mock_service('profile')

    def _mock_display_title(self):
        self.mock.instance.register_empty_response(
            service='organization',
            action='get_teams_for_profile_ids',
            mock_regex_lookup='organization:get_teams_for_profile_ids:.*',
        )

    def test_get_profile(self):
        expected = factories.ProfileFactory.create_protobuf(
            organization_id=self.organization.id,
        )
        self._mock_display_title()
        response = self.client.call_action(
            'get_profile',
            profile_id=expected.id,
        )
        self.verify_containers(expected, response.result.profile)

    def test_get_profile_authentication_identifier(self):
        expected = factories.ProfileFactory.create_protobuf(
            organization_id=self.organization.id,
        )
        self._mock_display_title()
        response = self.client.call_action(
            'get_profile',
            authentication_identifier=expected.authentication_identifier,
        )
        self.verify_containers(expected, response.result.profile)

    def test_get_profile_does_not_exist_authentication_identifier(self):
        with self.assertFieldError('authentication_identifier', 'DOES_NOT_EXIST'):
            self.client.call_action(
                'get_profile',
                authentication_identifier=fuzzy.FuzzyUUID().fuzz(),
            )

    def test_get_profile_full_name(self):
        profile = factories.ProfileFactory.create_protobuf()
        self.assertTrue(profile.full_name)

    def test_get_profile_invalid_profile_id(self):
        with self.assertFieldError('profile_id'):
            self.client.call_action(
                'get_profile',
                profile_id='invalid',
            )

    def test_get_profile_does_not_exist(self):
        with self.assertFieldError('profile_id', 'DOES_NOT_EXIST'):
            self.client.call_action(
                'get_profile',
                profile_id=fuzzy.FuzzyUUID().fuzz(),
            )

    def test_get_profile_email(self):
        expected = factories.ProfileFactory.create_protobuf(
            organization_id=self.organization.id,
        )
        self._mock_display_title()
        response = self.client.call_action(
            'get_profile',
            email=expected.email,
        )
        self.verify_containers(expected, response.result.profile)

    def test_update_profile_invalid_profile_id(self):
        self.profile.id = 'invalid'
        with self.assertFieldError('profile.id'):
            self.client.call_action('update_profile', profile=self.profile)

    def test_update_profile_does_not_exist(self):
        self.profile.id = fuzzy.FuzzyUUID().fuzz()
        with self.assertFieldError('profile.id', 'DOES_NOT_EXIST'):
            self.client.call_action('update_profile', profile=self.profile)

    def test_update_profile(self):
        original = factories.ProfileFactory.create_protobuf(
            organization_id=self.organization.id,
        )
        profile = profile_containers.ProfileV1()
        profile.CopyFrom(original)

        profile.first_name = 'Michael'
        profile.last_name = 'Hahn'
        profile.title = 'Engineer'

        # this has no effect, this just makes validating the container easier
        profile.full_name = 'Michael Hahn'

        response = self.client.call_action('update_profile', profile=profile)
        self.verify_containers(profile, response.result.profile)

    def test_bulk_create_profiles(self):
        profiles = []
        for _ in range(3):
            profiles.append(mocks.mock_profile())

        response = self.client.call_action('bulk_create_profiles', profiles=profiles)
        self.assertEqual(len(response.result.profiles), len(profiles))

    def test_bulk_create_profiles_dont_update_by_default(self):
        profiles = []
        for _ in range(3):
            profile = factories.ProfileFactory.create_protobuf(
                organization_id=self.organization.id,
            )
            profile.first_name = 'invalid'
            profiles.append(profile)

        response = self.client.call_action('bulk_create_profiles', profiles=profiles)
        for profile in response.result.profiles:
            self.assertNotEqual(profile.first_name, 'invalid')

    def test_bulk_create_profiles_should_update(self):
        profiles = []
        for _ in range(3):
            profile = factories.ProfileFactory.create_protobuf(
                organization_id=self.organization.id,
            )
            profile.first_name = 'invalid'
            profiles.append(profile)

        response = self.client.call_action(
            'bulk_create_profiles',
            profiles=profiles,
            should_update=True,
        )
        for profile in response.result.profiles:
            self.assertEqual(profile.first_name, 'invalid')

    def test_get_profiles_organization_id_by_default(self):
        response = self.client.call_action('get_profiles')
        self.assertTrue(response.success)
        self.assertEqual(len(response.result.profiles), 1)
        self.verify_containers(self.profile, response.result.profiles[0])

    def test_get_profiles_invalid_id_list(self):
        with self.assertFieldError('ids'):
            self.client.call_action('get_profiles', ids=['invalid'])

    def test_get_profiles_with_id_list(self):
        profiles = factories.ProfileFactory.create_batch(
            size=5,
            organization_id=self.organization.id,
        )
        response = self.client.call_action(
            'get_profiles',
            ids=[str(profile.id) for profile in profiles],
        )
        self.assertTrue(response.success)
        self.assertEqual(len(response.result.profiles), 5)

    def test_get_profiles_authentication_identifier(self):
        profiles = factories.ProfileFactory.create_batch(
            size=5,
            organization_id=self.organization.id,
        )
        response = self.client.call_action(
            'get_profiles',
            authentication_identifiers=[p.authentication_identifier for p in profiles[:2]],
        )
        self.assertEqual(len(response.result.profiles), 2)

    def test_get_profiles_with_location_id(self):
        profiles = factories.ProfileFactory.create_batch(
            size=5,
            organization_id=self.organization.id,
        )
        location_id = fuzzy.FuzzyUUID().fuzz()
        self.mock.instance.register_mock_object(
            'organization',
            'get_location_members',
            return_object_path='member_profile_ids',
            return_object=[str(profile.id) for profile in profiles[:3]],
            location_id=location_id,
        )
        response = self.client.call_action('get_profiles', location_id=location_id)
        self.assertEqual(len(response.result.profiles), 3)

    def test_get_profiles_with_location_id_invalid_location_id(self):
        with self.assertFieldError('location_id'):
            self.client.call_action('get_profiles', location_id='invalid')

    def test_get_profile_inflation_options(self):
        profile = factories.ProfileFactory.create_protobuf(
            organization_id=self.organization.id,
            contact_methods=[mocks.mock_contact_method(), mocks.mock_contact_method()],
        )
        response = self.client.call_action('get_profile', profile_id=profile.id)
        # verify objects are expanded by default
        self.assertEqual(len(response.result.profile.contact_methods), 2)

        response = self.client.call_action(
            'get_profile',
            profile_id=profile.id,
            inflations={'disabled': True},
        )
        self.assertFalse(response.result.profile.contact_methods)

        response = self.client.call_action(
            'get_profile',
            profile_id=profile.id,
            inflations={'only': ['contact_methods']},
        )
        self.assertEqual(len(response.result.profile.contact_methods), 2)

    def test_get_profiles_inflation_options(self):
        factories.ProfileFactory.create_batch(
            size=3,
            organization_id=self.organization.id,
            contact_methods=[
                mocks.mock_contact_method(id=None),
                mocks.mock_contact_method(id=None),
            ],
        )
        response = self.client.call_action('get_profiles')
        for profile in response.result.profiles:
            if profile.id != self.profile.id:
                self.assertEqual(len(profile.contact_methods), 2)

        response = self.client.call_action('get_profiles', inflations={'disabled': True})
        for profile in response.result.profiles:
            if profile.id != self.profile.id:
                self.assertFalse(profile.contact_methods)

        response = self.client.call_action(
            'get_profiles',
            inflations={'only': ['contact_methods']},
        )
        for profile in response.result.profiles:
            if profile.id != self.profile.id:
                self.assertEqual(len(profile.contact_methods), 2)

    def test_get_profiles_team_id_invalid(self):
        with self.assertFieldError('team_id'):
            self.client.call_action('get_profiles', team_id='invalid')

    def test_get_profiles_team_id(self):
        # create profiles not associated with our mock team
        factories.ProfileFactory.create_batch(size=3, organization_id=self.organization.id)

        # create profiles we'll return with the mock
        profiles = factories.ProfileFactory.create_batch(
            size=3,
            organization_id=self.organization.id,
        )
        team_id = fuzzy.FuzzyUUID().fuzz()
        self.mock.instance.register_mock_object(
            'organization',
            'get_descendants',
            return_object_path='profile_ids',
            return_object=[str(profile.id) for profile in profiles],
            team_id=team_id,
            direct=False,
        )

        response = self.client.call_action(
            'get_profiles',
            team_id=team_id,
            inflations={'disabled': True},
        )
        self.assertEqual(len(response.result.profiles), 3)

    def test_get_profiles_team_id_pagination_preserved(self):
        # create profiles not associated with our mock team
        factories.ProfileFactory.create_batch(size=3, organization_id=self.organization.id)

        # create profiles we'll return with the mock
        profiles = factories.ProfileFactory.create_batch(
            size=3,
            organization_id=self.organization.id,
        )
        team_id = fuzzy.FuzzyUUID().fuzz()

        # simulate the get_descendants call returning its own paginator
        response, extension = self.mock.get_mockable_action_response_and_extension(
            'organization',
            'get_descendants',
        )
        mock_paginator = soa_pb2.PaginatorV1(
            next_page=10,
            previous_page=9,
            total_pages=20,
        )
        response.control.paginator.CopyFrom(mock_paginator)
        response.result.success = True
        extension.profile_ids.extend([str(profile.id) for profile in profiles])
        self.mock.instance.register_mock_response(
            'organization',
            'get_descendants',
            response,
            mock_regex_lookup='organization:get_descendants:.*',
            is_action_response=True,
        )

        # make the call and ensure the paginator from the remote call was preserved
        response = self.client.call_action(
            'get_profiles',
            team_id=team_id,
            inflations={'disabled': True},
        )
        self.assertEqual(len(response.result.profiles), 3)
        self.assertEqual(response.control.paginator.next_page, 10)

    def test_get_profile_display_title(self):
        profile_team = mocks.mock_profile_team(profile_id=self.profile.id)
        self.mock.instance.register_mock_object(
            service='organization',
            action='get_teams_for_profile_ids',
            return_object_path='profiles_teams',
            return_object=[profile_team],
            profile_ids=[self.profile.id],
            fields={'only': ['name']},
        )
        response = self.client.call_action('get_profile', profile_id=self.profile.id)
        self.assertEqual(
            response.result.profile.display_title,
            '%s (%s)' % (self.profile.title, profile_team.team.name),
        )

    def test_get_profiles_emails(self):
        # create extra profiles
        factories.ProfileFactory.create_batch(size=3, organization_id=self.organization.id)

        # create profiles we'll fetch
        profiles = factories.ProfileFactory.create_batch(
            size=3,
            organization_id=self.organization.id,
        )
        response = self.client.call_action(
            'get_profiles',
            emails=[p.email for p in profiles],
            inflations={'disabled': True},
        )
        self.assertEqual(len(response.result.profiles), 3)
