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
        self.address = factories.AddressFactory.create(organization=self.organization)
        self.client = service.control.Client(
            'organization',
            token=mocks.mock_token(organization_id=str(self.organization.id)),
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
        response = self.client.call_action(
            'create_location',
            location={
                'organization_id': str(self.organization.id),
                'address': self.address.to_protobuf(),
                'name': fuzzy.FuzzyText().fuzz(),
            },
        )
        self.assertEqual(response.result.location.organization_id, str(self.organization.id))
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

    def test_update_location(self):
        new_name = 'New HQ'
        location = factories.LocationFactory.create_protobuf()
        location.name = new_name
        response = self.client.call_action('update_location', location=location)
        self.assertEqual(response.result.location.name, new_name)

    def test_get_location_invalid_location_id(self):
        with self.assertFieldError('location_id'):
            self.client.call_action('get_location', location_id='invalid')

    def test_get_location_does_not_exist(self):
        with self.assertFieldError('location_id', 'DOES_NOT_EXIST'):
            self.client.call_action('get_location', location_id=fuzzy.FuzzyUUID().fuzz())

    def test_get_location_with_location_id(self):
        location = factories.LocationFactory.create_protobuf()
        with self.mock_transport(self.client) as mock:
            self._mock_get_profile_stats(mock, [str(location.id)])
            response = self.client.call_action('get_location', location_id=location.id)
        self.verify_containers(location, response.result.location)
        self.assertEqual(response.result.location.profile_count, 5)

    def test_get_location_by_name_organization_id_required(self):
        with self.assertFieldError('organization_id', 'REQUIRED'):
            self.client.call_action('get_location', name=fuzzy.FuzzyText().fuzz())

    def test_get_location_by_name(self):
        location = factories.LocationFactory.create_protobuf()
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
        locations = factories.LocationFactory.create_batch(
            size=3,
            organization=self.organization,
        )
        factories.LocationFactory.create_batch(size=3)
        with self.mock_transport(self.client) as mock:
            self._mock_get_profile_stats(mock, [str(location.id) for location in locations])
            response = self.client.call_action(
                'get_locations',
                organization_id=str(self.organization.id),
            )
        self.assertEqual(len(locations), len(response.result.locations))
        for location in response.result.locations:
            self.assertEqual(location.profile_count, 5)
