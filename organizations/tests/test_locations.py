import uuid

import arrow

import service.control
from services.test import (
    fuzzy,
    mocks,
    TestCase,
)

from .. import factories


class OrganizationLocationTests(TestCase):

    def setUp(self):
        super(OrganizationLocationTests, self).setUp()
        self.organization = factories.OrganizationFactory.create()
        self.profile = mocks.mock_profile(organization_id=str(self.organization.id))
        self.address = factories.AddressFactory.create(organization=self.organization)
        self.client = service.control.Client(
            'organization',
            token=mocks.mock_token(
                organization_id=str(self.organization.id),
                profile_id=self.profile.id,
            ),
        )

    def _mock_get_profile_stats(self, mock, location_ids):
        service = 'profile'
        action = 'get_profile_stats'
        mock_response = mock.get_mockable_response(service, action)
        for location_id in location_ids:
            stat = mock_response.stats.add()
            stat.id = location_id
            stat.count = 5

        mock.instance.register_mock_response(
            service,
            action,
            mock_response,
            location_ids=location_ids,
        )

    def test_create_location_invalid_organization_id(self):
        with self.assertFieldError('location.organization_id'):
            self.client.call_action(
                'create_location',
                location={
                    'organization_id': 'invalid',
                    'address': self.address.to_protobuf(),
                    'name': fuzzy.FuzzyText().fuzz(),
                },
            )

    def test_create_location_invalid_address_id(self):
        address = mocks.mock_address(id='invalid')
        with self.assertFieldError('location.address.id'):
            self.client.call_action(
                'create_location',
                location={
                    'organization_id': fuzzy.FuzzyUUID().fuzz(),
                    'address': address,
                    'name': fuzzy.FuzzyText().fuzz(),
                },
            )

    def test_create_location(self):
        established_date = str(arrow.utcnow().date())
        response = self.client.call_action(
            'create_location',
            location={
                'organization_id': str(self.organization.id),
                'address': self.address.to_protobuf(),
                'name': fuzzy.FuzzyText().fuzz(),
                'established_date': established_date,
            },
        )
        self.assertEqual(response.result.location.organization_id, str(self.organization.id))
        self.assertEqual(established_date, response.result.location.established_date)
        self.verify_containers(response.result.location.address, self.address.to_protobuf())

    def test_create_location_duplicate(self):
        location = factories.LocationFactory.create_protobuf()
        with self.assertFieldError('location', 'DUPLICATE'):
            self.client.call_action(
                'create_location',
                location={
                    'organization_id': location.organization_id,
                    'address': location.address,
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

    def _update_location(self, location, points_of_contact=None):
        with self.mock_transport(self.client) as mock:
            self._mock_get_profile_stats(mock, [str(location.id)])
            mock.instance.register_mock_object(
                service='profile',
                action='get_profile',
                return_object_path='profile',
                return_object=self.profile,
                profile_id=self.profile.id,
            )
            mock.instance.register_empty_response(
                'history',
                'record_action',
                mock_regex_lookup='history:record_action:.*',
            )
            if points_of_contact:
                mock.instance.register_mock_object(
                    'profile',
                    'get_profiles',
                    return_object_path='profiles',
                    return_object=points_of_contact,
                    ids=[profile.id for profile in points_of_contact],
                )
            return self.client.call_action('update_location', location=location)

    def test_update_location(self):
        self.profile.is_admin = True
        new_name = 'New HQ'
        new_description = 'updated'
        location = factories.LocationFactory.create_protobuf()
        location.name = new_name
        location.location_description.value = new_description
        points_of_contact = [mocks.mock_profile(), mocks.mock_profile()]
        location.points_of_contact.extend(points_of_contact)

        # update location
        response = self._update_location(location, points_of_contact)
        self.assertEqual(response.result.location.name, new_name)
        self.assertEqual(response.result.location.location_description.value, new_description)
        self.assertEqualUUID4(
            response.result.location.location_description.by_profile_id,
            self.profile.id,
        )
        self.assertTrue(response.result.location.location_description.changed)
        self.assertEqual(len(response.result.location.points_of_contact), len(points_of_contact))

        # update the location again with a new description
        location = response.result.location
        location.location_description.value = 'another description'
        response = self._update_location(location, points_of_contact)
        location_description = response.result.location.location_description
        self.assertEqual(location_description.value, location.location_description.value)
        self.assertNotEqual(location_description.changed, location.location_description.changed)

    def test_update_location_non_admin(self):
        location = factories.LocationFactory.create_protobuf()
        location.name = 'updated'
        with self.mock_transport() as mock, self.assertRaisesCallActionError() as expected:
            mock.instance.register_mock_object(
                service='profile',
                action='get_profile',
                return_object_path='profile',
                return_object=self.profile,
                profile_id=self.profile.id,
            )
            self.client.call_action('update_location', location=location)
        self.assertIn('PERMISSION_DENIED', expected.exception.response.errors)

    def test_get_location_invalid_location_id(self):
        with self.assertFieldError('location_id'):
            self.client.call_action('get_location', location_id='invalid')

    def test_get_location_does_not_exist(self):
        with self.assertFieldError('location_id', 'DOES_NOT_EXIST'):
            self.client.call_action('get_location', location_id=fuzzy.FuzzyUUID().fuzz())

    def test_get_location_with_location_id_non_admin(self):
        self.profile.is_admin = False
        location = factories.LocationFactory.create_protobuf()
        with self.mock_transport(self.client) as mock:
            mock.instance.register_mock_object(
                service='profile',
                action='get_profile',
                return_object_path='profile',
                return_object=self.profile,
                profile_id=self.profile.id,
            )
            self._mock_get_profile_stats(mock, [str(location.id)])
            response = self.client.call_action('get_location', location_id=location.id)
        self.verify_containers(location, response.result.location)
        self.assertEqual(response.result.location.profile_count, 5)
        permissions = response.result.location.permissions
        self.assertFalse(permissions.can_edit)
        self.assertFalse(permissions.can_add)
        self.assertFalse(permissions.can_delete)

    def test_get_location_with_location_id_admin(self):
        self.profile.is_admin = True
        location = factories.LocationFactory.create_protobuf()
        with self.mock_transport(self.client) as mock:
            mock.instance.register_mock_object(
                service='profile',
                action='get_profile',
                return_object_path='profile',
                return_object=self.profile,
                profile_id=self.profile.id,
            )
            self._mock_get_profile_stats(mock, [str(location.id)])
            response = self.client.call_action('get_location', location_id=location.id)
        self.verify_containers(location, response.result.location)
        self.assertEqual(response.result.location.profile_count, 5)
        permissions = response.result.location.permissions
        self.assertTrue(permissions.can_edit)
        self.assertTrue(permissions.can_add)
        self.assertTrue(permissions.can_delete)

    def test_get_location_by_name_organization_id_required(self):
        with self.assertFieldError('organization_id', 'REQUIRED'):
            self.client.call_action('get_location', name=fuzzy.FuzzyText().fuzz())

    def test_get_location_by_name(self):
        location = factories.LocationFactory.create_protobuf()
        with self.mock_transport() as mock:
            mock.instance.register_mock_object(
                service='profile',
                action='get_profile',
                return_object_path='profile',
                return_object=self.profile,
                profile_id=self.profile.id,
            )
            self._mock_get_profile_stats(mock, [str(location.id)])
            response = self.client.call_action(
                'get_location',
                name=location.name,
                organization_id=location.organization_id,
            )
        self.verify_containers(location, response.result.location)

    def test_get_locations_no_locations(self):
        response = self.client.call_action('get_locations')
        self.assertEqual(len(response.result.locations), 0)

    def test_get_locations(self):
        self.profile.is_admin = True
        points_of_contact = [mocks.mock_profile(), mocks.mock_profile()]
        locations = factories.LocationFactory.create_batch(
            size=3,
            organization=self.organization,
            points_of_contact_profile_ids=[profile.id for profile in points_of_contact],
        )
        factories.LocationFactory.create_batch(size=3)
        with self.mock_transport(self.client) as mock:
            mock.instance.register_mock_object(
                service='profile',
                action='get_profile',
                return_object_path='profile',
                return_object=self.profile,
                profile_id=self.profile.id,
            )
            mock.instance.register_mock_object(
                service='profile',
                action='get_profiles',
                return_object_path='profiles',
                return_object=points_of_contact,
                ids=[str(uuid.UUID(profile.id, version=4)) for profile in points_of_contact],
            )
            self._mock_get_profile_stats(mock, [str(location.id) for location in locations])
            response = self.client.call_action(
                'get_locations',
                organization_id=str(self.organization.id),
            )
        self.assertEqual(len(locations), len(response.result.locations))
        for location in response.result.locations:
            self.assertEqual(location.profile_count, 5)
            self.assertEqual(len(location.points_of_contact), len(points_of_contact))
            self.assertTrue(location.permissions.can_edit)
            self.assertTrue(location.permissions.can_add)
            self.assertTrue(location.permissions.can_delete)
