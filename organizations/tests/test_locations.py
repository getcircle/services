import uuid

import arrow

import service.control
from services.test import (
    fuzzy,
    mocks,
    MockedTestCase,
)

from .. import factories


class OrganizationLocationTests(MockedTestCase):

    def setUp(self):
        super(OrganizationLocationTests, self).setUp()
        self.organization = factories.OrganizationFactory.create()
        self.profile = mocks.mock_profile(organization_id=str(self.organization.id))
        self.client = service.control.Client(
            'organization',
            token=mocks.mock_token(
                organization_id=str(self.organization.id),
                profile_id=self.profile.id,
            ),
        )
        self.mock.instance.dont_mock_service('organization')

    def _mock_requester_profile(self):
        self.mock.instance.register_mock_object(
            service='profile',
            action='get_profile',
            return_object_path='profile',
            return_object=self.profile,
            profile_id=self.profile.id,
            inflations={'enabled': False},
        )

    def _build_location_protobuf(self, **kwargs):
        kwargs['organization'] = kwargs.get('organization', self.organization)
        return factories.LocationFactory.build_protobuf(**kwargs)

    def test_create_location(self):
        location = self._build_location_protobuf(established_date=arrow.utcnow().date())
        response = self.client.call_action('create_location', location=location)
        self.assertEqual(response.result.location.organization_id, str(self.organization.id))
        self.verify_containers(location, response.result.location)

    def test_create_location_duplicate(self):
        location = factories.LocationFactory.create_protobuf(organization=self.organization)
        location.ClearField('id')
        with self.assertFieldError('location', 'DUPLICATE'):
            self.client.call_action('create_location', location=location)

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
        self.mock.instance.register_mock_object(
            service='profile',
            action='get_profile',
            return_object_path='profile',
            return_object=self.profile,
            profile_id=self.profile.id,
            inflations={'enabled': False},
        )
        self.mock.instance.register_empty_response(
            'history',
            'record_action',
            mock_regex_lookup='history:record_action:.*',
        )
        if points_of_contact:
            self.mock.instance.register_mock_object(
                'profile',
                'get_profiles',
                return_object_path='profiles',
                return_object=points_of_contact,
                ids=[profile.id for profile in points_of_contact],
                inflations={'only': ['contact_methods']},
            )
        return self.client.call_action('update_location', location=location)

    def test_update_location(self):
        self.profile.is_admin = True
        new_name = 'New HQ'
        new_description = 'updated'
        location = factories.LocationFactory.create_protobuf(organization=self.organization)
        location.name = new_name
        location.description.value = new_description
        points_of_contact = [mocks.mock_profile(), mocks.mock_profile()]
        location.points_of_contact.extend(points_of_contact)

        # update location
        response = self._update_location(location, points_of_contact)
        self.assertEqual(response.result.location.name, new_name)
        self.assertEqual(response.result.location.description.value, new_description)
        self.assertEqualUUID4(response.result.location.description.by_profile_id, self.profile.id)
        self.assertTrue(response.result.location.description.changed)
        self.assertEqual(len(response.result.location.points_of_contact), len(points_of_contact))
        self.verify_containers(self.profile, response.result.location.description.by_profile)

        # update the location again with a new description
        location = response.result.location
        location.description.value = 'another description'
        response = self._update_location(location, points_of_contact)
        description = response.result.location.description
        self.assertEqual(description.value, location.description.value)
        self.assertNotEqual(description.changed, location.description.changed)

    def test_update_location_non_admin(self):
        location = factories.LocationFactory.create_protobuf()
        location.name = 'updated'
        self.mock.instance.register_mock_object(
            service='profile',
            action='get_profile',
            return_object_path='profile',
            return_object=self.profile,
            profile_id=self.profile.id,
            mock_regex_lookup='profile:get_profile:.*',
        )
        with self.assertRaisesCallActionError() as expected:
            self.client.call_action('update_location', location=location)
        self.assertIn('PERMISSION_DENIED', expected.exception.response.errors)

    def test_get_location_invalid_location_id(self):
        with self.assertFieldError('location_id'):
            self.client.call_action('get_location', location_id='invalid')

    def test_get_location_does_not_exist(self):
        with self.assertFieldError('location_id', 'DOES_NOT_EXIST'):
            self.client.call_action('get_location', location_id=fuzzy.FuzzyUUID().fuzz())

    def test_get_location_name_does_not_exist(self):
        with self.assertFieldError('name', 'DOES_NOT_EXIST'):
            self.client.call_action('get_location', name='invalid')

    def test_get_location_with_name(self):
        location = factories.LocationFactory.create(organization=self.organization)
        self.mock.instance.register_mock_object(
            service='profile',
            action='get_profile',
            return_object_path='profile',
            return_object=self.profile,
            profile_id=self.profile.id,
            mock_regex_lookup='profile:get_profile:.*',
        )
        response = self.client.call_action('get_location', name=str(location.name))
        self.verify_containers(location.to_protobuf(), response.result.location)

    def test_get_location_with_location_id_non_admin(self):
        self.profile.is_admin = False
        location = factories.LocationFactory.create(organization=self.organization)
        factories.LocationMemberFactory.create_batch(
            size=5,
            location=location,
            organization=self.organization,
        )
        self.mock.instance.register_mock_object(
            service='profile',
            action='get_profile',
            return_object_path='profile',
            return_object=self.profile,
            profile_id=self.profile.id,
            mock_regex_lookup='profile:get_profile:.*',
        )
        response = self.client.call_action('get_location', location_id=str(location.id))
        self.verify_containers(location.to_protobuf(), response.result.location)
        self.assertEqual(response.result.location.profile_count, 5)
        permissions = response.result.location.permissions
        self.assertFalse(permissions.can_edit)
        self.assertFalse(permissions.can_add)
        self.assertFalse(permissions.can_delete)

    def test_get_location_with_location_id_non_admin_member_of_location(self):
        self.profile.is_admin = False
        location = factories.LocationFactory.create(organization=self.organization)
        factories.LocationMemberFactory.create(
            profile_id=self.profile.id,
            location=location,
            organization=self.organization,
        )
        with self.mock_transport(self.client) as mock:
            mock.instance.register_mock_object(
                service='profile',
                action='get_profile',
                return_object_path='profile',
                return_object=self.profile,
                profile_id=self.profile.id,
            )
            response = self.client.call_action('get_location', location_id=str(location.id))
        self.verify_containers(location.to_protobuf(), response.result.location)
        self.assertEqual(response.result.location.profile_count, 1)
        permissions = response.result.location.permissions
        self.assertTrue(permissions.can_edit)
        self.assertFalse(permissions.can_add)
        self.assertFalse(permissions.can_delete)

    def test_get_location_with_location_id_admin(self):
        self.profile.is_admin = True
        location = factories.LocationFactory.create_protobuf(organization=self.organization)
        self.mock.instance.register_mock_object(
            service='profile',
            action='get_profile',
            return_object_path='profile',
            return_object=self.profile,
            profile_id=self.profile.id,
            mock_regex_lookup='profile:get_profile:.*',
        )
        response = self.client.call_action('get_location', location_id=location.id)
        self.verify_containers(location, response.result.location)
        permissions = response.result.location.permissions
        self.assertTrue(permissions.can_edit)
        self.assertTrue(permissions.can_add)
        self.assertTrue(permissions.can_delete)

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
        for location in locations:
            factories.LocationMemberFactory.create_batch(
                size=3,
                location=location,
                organization=self.organization,
            )

        factories.LocationFactory.create_batch(size=3)
        self.mock.instance.register_mock_object(
            service='profile',
            action='get_profile',
            return_object_path='profile',
            return_object=self.profile,
            profile_id=self.profile.id,
            mock_regex_lookup='profile:get_profile:.*',
        )
        self.mock.instance.register_mock_object(
            service='profile',
            action='get_profiles',
            return_object_path='profiles',
            return_object=points_of_contact,
            ids=[str(uuid.UUID(profile.id, version=4)) for profile in points_of_contact],
            inflations={'only': ['contact_methods']},
        )
        response = self.client.call_action('get_locations')
        self.assertEqual(len(locations), len(response.result.locations))
        for location in response.result.locations:
            self.assertEqual(location.profile_count, 3)
            self.assertEqual(len(location.points_of_contact), len(points_of_contact))
            self.assertTrue(location.permissions.can_edit)
            self.assertTrue(location.permissions.can_add)
            self.assertTrue(location.permissions.can_delete)

    def test_get_locations_profile_id_invalid(self):
        with self.assertFieldError('profile_id'):
            self.client.call_action('get_locations', profile_id='invalid')

    def test_get_locations_profile_id(self):
        # create some locations for an org
        locations = factories.LocationFactory.create_batch(
            size=3,
            organization=self.organization,
        )
        factories.LocationMemberFactory.create(
            organization=self.organization,
            location=locations[0],
            profile_id=self.profile.id,
        )
        response = self.client.call_action('get_locations', profile_id=self.profile.id)
        self.assertEqual(len(response.result.locations), 1)
        self.verify_containers(locations[0].to_protobuf(), response.result.locations[0])

        factories.LocationMemberFactory.create(
            organization=self.organization,
            location=locations[1],
            profile_id=self.profile.id,
        )
        response = self.client.call_action('get_locations', profile_id=self.profile.id)
        self.assertEqual(len(response.result.locations), 2)

    def test_get_location_members_invalid_location_id(self):
        with self.assertFieldError('location_id'):
            self.client.call_action('get_location_members', location_id='invalid')

    def test_get_location_members_location_id_required(self):
        with self.assertFieldError('location_id', 'MISSING'):
            self.client.call_action('get_location_members')

    def test_get_location_members_does_not_exist(self):
        with self.assertFieldError('location_id', 'DOES_NOT_EXIST'):
            self.client.call_action('get_location_members', location_id=fuzzy.FuzzyUUID().fuzz())

    def test_get_location_members(self):
        location = factories.LocationFactory.create(organization=self.organization)
        # create members for this location
        factories.LocationMemberFactory.create_batch(
            size=3,
            location=location,
            organization=self.organization,
        )

        # create members for other locations
        factories.LocationMemberFactory.create_batch(size=3, organization=self.organization)
        response = self.client.call_action('get_location_members', location_id=str(location.id))
        self.assertEqual(len(response.result.member_profile_ids), 3)

    def test_add_location_members_invalid_location_id(self):
        with self.assertFieldError('location_id'):
            self.client.call_action(
                'add_location_members',
                location_id='invalid',
                profile_ids=[fuzzy.FuzzyUUID().fuzz()],
            )

    def test_add_location_members_location_id_required(self):
        with self.assertFieldError('location_id', 'MISSING'):
            self.client.call_action(
                'add_location_members',
                profile_ids=[fuzzy.FuzzyUUID().fuzz()],
            )

    def test_add_location_members_location_id_does_not_exist(self):
        with self.assertFieldError('location_id', 'DOES_NOT_EXIST'):
            self.client.call_action(
                'add_location_members',
                location_id=fuzzy.FuzzyUUID().fuzz(),
                profile_ids=[fuzzy.FuzzyUUID().fuzz()],
            )

    def test_add_location_members_profile_ids_required(self):
        location = factories.LocationFactory.create_protobuf(organization=self.organization)
        with self.assertFieldError('profile_ids', 'MISSING'):
            self.client.call_action('add_location_members', location_id=location.id)

    def test_add_location_members_profile_ids_invalid(self):
        location = factories.LocationFactory.create_protobuf(organization=self.organization)
        with self.assertFieldError('profile_ids'):
            self.client.call_action(
                'add_location_members',
                location_id=location.id,
                profile_ids=['invalid'],
            )

    def test_add_location_members(self):
        location = factories.LocationFactory.create_protobuf(organization=self.organization)
        self.client.call_action(
            'add_location_members',
            location_id=location.id,
            profile_ids=[fuzzy.FuzzyUUID().fuzz(), fuzzy.FuzzyUUID().fuzz()],
        )
        self.mock.instance.register_mock_object(
            'profile',
            'get_profile',
            return_object_path='profile',
            return_object=self.profile,
            mock_regex_lookup='profile:get_profile:.*',
        )
        response = self.client.call_action('get_location', location_id=location.id)
        self.assertEqual(response.result.location.profile_count, 2)

    def test_get_locations_inflations(self):
        self.profile.is_admin = True
        points_of_contact = [mocks.mock_profile(), mocks.mock_profile()]
        self._mock_requester_profile()
        locations = factories.LocationFactory.create_batch(
            size=3,
            organization=self.organization,
            points_of_contact_profile_ids=[profile.id for profile in points_of_contact],
            description=mocks.mock_description(by_profile_id=str(self.profile.id)),
        )
        for location in locations:
            factories.LocationMemberFactory.create_batch(
                size=3,
                location=location,
                organization=self.organization,
            )

        factories.LocationFactory.create_batch(size=3)
        self.mock.instance.register_mock_object(
            service='profile',
            action='get_profiles',
            return_object_path='profiles',
            return_object=points_of_contact,
            ids=[str(uuid.UUID(profile.id, version=4)) for profile in points_of_contact],
            inflations={'only': ['contact_methods']},
        )
        response = self.client.call_action('get_locations')

        self.assertEqual(len(locations), len(response.result.locations))
        for location in response.result.locations:
            self.assertEqual(location.profile_count, 3)
            self.assertEqual(len(location.points_of_contact), len(points_of_contact))
            self.assertTrue(location.permissions.can_edit)
            self.assertTrue(location.permissions.can_add)
            self.assertTrue(location.permissions.can_delete)

        self.mock.instance.dont_mock_service('organization')
        self.mock.instance.register_mock_object(
            service='profile',
            action='get_profiles',
            return_object_path='profiles',
            return_object=points_of_contact,
            ids=[str(uuid.UUID(profile.id, version=4)) for profile in points_of_contact],
            inflations={'only': ['contact_methods']},
        )
        response = self.client.call_action(
            'get_locations',
            inflations={'exclude': ['permissions']},
        )
        for location in response.result.locations:
            self.assertEqual(location.profile_count, 3)
            self.assertEqual(len(location.points_of_contact), len(points_of_contact))
            self.assertFalse(location.permissions.can_edit)
            self.assertFalse(location.permissions.can_add)
            self.assertFalse(location.permissions.can_delete)

        response = self.client.call_action(
            'get_locations',
            inflations={'only': ['points_of_contact']},
        )
        for location in response.result.locations:
            self.assertEqual(location.profile_count, 0)
            self.assertEqual(len(location.points_of_contact), len(points_of_contact))
            self.assertFalse(location.permissions.can_edit)
            self.assertFalse(location.permissions.can_add)
            self.assertFalse(location.permissions.can_delete)

        response = self.client.call_action(
            'get_locations',
            inflations={'enabled': False},
        )
        for location in response.result.locations:
            self.assertEqual(location.profile_count, 0)
            self.assertFalse(location.points_of_contact)
            self.assertFalse(location.permissions.can_edit)
            self.assertFalse(location.permissions.can_add)
            self.assertFalse(location.permissions.can_delete)

    def test_get_locations_with_ids(self):
        locations = factories.LocationFactory.create_batch(
            size=3,
            organization=self.organization,
        )
        factories.LocationFactory.create_batch(size=3)
        self.mock.instance.register_mock_object(
            service='profile',
            action='get_profile',
            return_object_path='profile',
            return_object=self.profile,
            profile_id=self.profile.id,
            mock_regex_lookup='profile:get_profile:.*',
        )
        response = self.client.call_action('get_locations', ids=[str(l.id) for l in locations][:2])
        self.assertEqual(2, len(response.result.locations))
