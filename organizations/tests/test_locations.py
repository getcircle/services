import base64

from protobufs.profile_service_pb2 import ProfileService
import service.control
from services.test import (
    fuzzy,
    mocks,
    TestCase,
)

from .. import (
    factories,
    models,
)


class AppreciationTests(TestCase):

    def setUp(self):
        super(AppreciationTests, self).setUp()
        self.client = service.control.Client('organization', token=mocks.mock_token())

    def test_create_location_invalid_organization_id(self):
        with self.assertFieldError('location.organization_id'):
            self.client.call_action(
                'create_location',
                location={
                    'organization_id': 'invalid',
                    'address_id': fuzzy.FuzzyUUID().fuzz(),
                    'name': fuzzy.FuzzyText().fuzz(),
                },
            )

    def test_create_location_invalid_address_id(self):
        with self.assertFieldError('location.address_id'):
            self.client.call_action(
                'create_location',
                location={
                    'organization_id': fuzzy.FuzzyUUID().fuzz(),
                    'address_id': 'invalid',
                    'name': fuzzy.FuzzyText().fuzz(),
                },
            )

    def test_create_location(self):
        organization_id = fuzzy.FuzzyUUID().fuzz()
        address_id = fuzzy.FuzzyUUID().fuzz()
        response = self.client.call_action(
            'create_location',
            location={
                'organization_id': organization_id,
                'address_id': address_id,
                'name': fuzzy.FuzzyText().fuzz(),
            },
        )
        self.assertEqual(response.result.location.organization_id, organization_id)
        self.assertEqual(response.result.location.address_id, address_id)

    def test_create_location_duplicate(self):
        location = factories.LocationFactory.create_protobuf()
        with self.assertFieldError('location', 'DUPLICATE'):
            self.client.call_action(
                'create_location',
                location={
                    'organization_id': location.organization_id,
                    'address_id': fuzzy.FuzzyUUID().fuzz(),
                    'name': location.name,
                },
            )

    def test_update_location_does_not_exist(self):
        location = factories.LocationFactory.build_protobuf()
        with self.assertFieldError('location.id', 'DOES_NOT_EXIST'):
            self.client.call_action('update_location', location=location)

    def test_update_location_invalid_location_id(self):
        location = factories.LocationFactory.build_protobuf()
        location.id = 'invalid'
        with self.assertFieldError('location.id'):
            self.client.call_action('update_location', location=location)

    def test_update_location(self):
        new_name = 'New HQ'
        location = factories.LocationFactory.create_protobuf()
        location.name = new_name
        response = self.client.call_action('update_location', location=location)
        self.assertEqual(response.result.location.name, new_name)

    def test_get_extended_location_does_not_exist(self):
        location = factories.LocationFactory.build_protobuf()
        with self.assertFieldError('location_id', 'DOES_NOT_EXIST'):
            self.client.call_action('get_extended_location', location_id=location.id)

    def test_get_extended_location_invalid_location_id(self):
        with self.assertFieldError('location_id'):
            self.client.call_action('get_extended_location', location_id='invalid')

    def _mock_get_profiles_for_location(self, mock, location_id, profiles=3):
        service = 'profile'
        action = 'get_profiles'
        mock_response = mock.get_mockable_response(service, action)
        profiles_list = []
        for _ in range(profiles):
            profile = mock_response.profiles.add()
            mocks.mock_profile(profile)
            profiles_list.append(profile)

        mock.instance.register_mock_response(
            service,
            action,
            mock_response,
            location_id=location_id,
        )
        return profiles_list

    def test_get_extended_location(self):
        location = factories.LocationFactory.create()
        location_protobuf = factories.LocationFactory.to_protobuf(location)
        address_protobuf = factories.AddressFactory.to_protobuf(location.address)
        profiles = []
        teams = []
        with self.default_mock_transport(self.client) as mock:
            profiles = self._mock_get_profiles_for_location(mock, str(location.id))
            for profile in profiles:
                teams.append(factories.TeamFactory.create(id=profile.team_id))

            response = self.client.call_action(
                'get_extended_location',
                location_id=str(location.id),
            )

        self._verify_containers(location_protobuf, response.result.location)
        self._verify_containers(address_protobuf, response.result.address)

        profiles_payload = base64.decodestring(response.result.member_profiles_payload)
        response_profiles = ProfileService.Containers.ProfileArray.FromString(profiles_payload)
        self.assertEqual(len(response_profiles.items), len(profiles))

        self.assertEqual(len(response.result.teams), len(teams))
