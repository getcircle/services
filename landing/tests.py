import service.control
import service.settings
from service.transports import local
from service.transports import mock

from services.test import (
    fuzzy,
    TestCase,
)


class TestLandingService(TestCase):

    def setUp(self):
        service.settings.DEFAULT_TRANSPORT = 'service.transports.mock.instance'
        self.client = service.control.Client('landing', token='test-token')
        self.client.set_transport(local.instance)

    def tearDown(self):
        service.settings.DEFAULT_TRANSPORT = 'service.transports.local.instance'

    def _mock_profile(self, profile):
        profile.id = fuzzy.FuzzyUUID().fuzz()
        profile.organization_id = fuzzy.FuzzyUUID().fuzz()
        profile.title = fuzzy.FuzzyText().fuzz()
        profile.full_name = fuzzy.FuzzyText().fuzz()

    def _mock_address(self, address):
        address.id = fuzzy.FuzzyUUID().fuzz()
        address.address_1 = fuzzy.FuzzyText().fuzz()
        address.address_2 = fuzzy.FuzzyText().fuzz()
        address.city = fuzzy.FuzzyText().fuzz()
        address.region = fuzzy.FuzzyText().fuzz()
        address.postal_code = '94010'
        address.country_code = 'US'
        return address

    def _mock_get_profile(self, profile_id=None):
        service = 'profile'
        action = 'get_profile'
        mock_response = mock.get_mockable_response(service, action)
        self._mock_profile(mock_response.profile)
        if profile_id is not None:
            mock_response.profile.id = profile_id

        mock.instance.register_mock_response(
            service,
            action,
            mock_response,
            profile_id=mock_response.profile.id,
        )
        return mock_response.profile

    def _mock_get_peers(self, profile_id, peers=3):
        service = 'profile'
        action = 'get_peers'
        mock_response = mock.get_mockable_response(service, action)
        for _ in range(peers):
            profile = mock_response.profiles.add()
            self._mock_profile(profile)

        mock.instance.register_mock_response(service, action, mock_response, profile_id=profile_id)

    def _mock_get_direct_reports(self, profile_id, direct_reports=3):
        service = 'profile'
        action = 'get_direct_reports'
        mock_response = mock.get_mockable_response(service, action)
        for _ in range(direct_reports):
            profile = mock_response.profiles.add()
            self._mock_profile(profile)

        mock.instance.register_mock_response(service, action, mock_response, profile_id=profile_id)

    def _mock_get_addresses(self, organization_id, addresses=3):
        service = 'organization'
        action = 'get_addresses'
        mock_response = mock.get_mockable_response(service, action)
        address_list = []
        for _ in range(addresses):
            address = mock_response.addresses.add()
            address_list.append(self._mock_address(address))

        mock.instance.register_mock_response(
            service,
            action,
            mock_response,
            organization_id=organization_id,
        )
        return address_list

    def _mock_get_profile_stats(self, address_ids, count=3):
        service = 'profile'
        action = 'get_profile_stats'
        mock_response = mock.get_mockable_response(service, action)
        for address_id in address_ids:
            container = mock_response.stats.add()
            container.id = address_id
            container.count = str(count)

        mock.instance.register_mock_response(
            service,
            action,
            mock_response,
            address_ids=address_ids,
        )

    def _mock_get_upcoming_anniversaries(self, organization_id, profiles=3):
        service = 'profile'
        action = 'get_upcoming_anniversaries'
        mock_response = mock.get_mockable_response(service, action)
        for _ in range(profiles):
            profile = mock_response.profiles.add()
            self._mock_profile(profile)

        mock.instance.register_mock_response(
            service,
            action,
            mock_response,
            organization_id=organization_id,
        )

    def test_profile_category_invalid_profile_id(self):
        response = self.client.call_action('get_categories', profile_id='invalid')
        self._verify_field_error(response, 'profile_id')

    def test_peers_profile_category(self):
        profile = self._mock_get_profile()
        self._mock_get_peers(profile.id)
        self._mock_get_direct_reports(profile.id, direct_reports=0)
        self._mock_get_addresses(profile.organization_id, addresses=0)
        self._mock_get_profile_stats([])
        self._mock_get_upcoming_anniversaries(profile.organization_id, profiles=0)

        response = self.client.call_action('get_categories', profile_id=profile.id)
        self.assertTrue(response.success)
        self.assertEqual(len(response.result.profile_categories), 1)

        category = response.result.profile_categories[0]
        self.assertEqual(category.title, 'Peers')
        self.assertEqual(len(category.content), 3)
        self.assertEqual(category.content_key, 'title')

    def test_direct_reports_profile_category(self):
        profile = self._mock_get_profile()
        self._mock_get_peers(profile.id, peers=0)
        self._mock_get_direct_reports(profile.id)
        self._mock_get_addresses(profile.organization_id, addresses=0)
        self._mock_get_profile_stats([])
        self._mock_get_upcoming_anniversaries(profile.organization_id, profiles=0)

        response = self.client.call_action('get_categories', profile_id=profile.id)
        self.assertTrue(response.success)
        self.assertEqual(len(response.result.profile_categories), 1)

        category = response.result.profile_categories[0]
        self.assertEqual(category.title, 'Direct Reports')
        self.assertEqual(len(category.content), 3)
        self.assertEqual(category.content_key, 'title')

    def test_locations_address_category(self):
        profile = self._mock_get_profile()
        self._mock_get_peers(profile.id, peers=0)
        self._mock_get_direct_reports(profile.id, direct_reports=0)
        addresses = self._mock_get_addresses(profile.organization_id)
        self._mock_get_profile_stats([a.id for a in addresses])
        self._mock_get_upcoming_anniversaries(profile.organization_id, profiles=0)

        response = self.client.call_action('get_categories', profile_id=profile.id)
        self.assertTrue(response.success)
        self.assertEqual(len(response.result.address_categories), 1)

        category = response.result.address_categories[0]
        self.assertEqual(category.title, 'Locations')
        self.assertEqual(len(category.content), 3)
        self.assertEqual(category.content_key, 'address_1')
        for address in category.content:
            self.assertEqual(address.profile_count, '3')

    def test_anniversaries_profile_category(self):
        profile = self._mock_get_profile()
        self._mock_get_peers(profile.id, peers=0)
        self._mock_get_direct_reports(profile.id, direct_reports=0)
        self._mock_get_addresses(profile.organization_id, addresses=0)
        self._mock_get_profile_stats([])
        self._mock_get_upcoming_anniversaries(profile.organization_id)

        response = self.client.call_action('get_categories', profile_id=profile.id)
        self.assertTrue(response.success)
        self.assertEqual(len(response.result.profile_categories), 1)

        category = response.result.profile_categories[0]
        self.assertEqual(category.title, 'Work Anniversaries')
        self.assertEqual(len(category.content), 3)
        self.assertEqual(category.content_key, 'hire_date')
