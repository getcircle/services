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
        profile.title = fuzzy.FuzzyText().fuzz()
        profile.full_name = fuzzy.FuzzyText().fuzz()

    def test_profile_category_invalid_profile_id(self):
        response = self.client.call_action('get_categories', profile_id='invalid')
        self._verify_field_error(response, 'profile_id')

    def test_peers_profile_category(self):
        mock_response = mock.get_mockable_response('profile', 'get_peers')
        for _ in range(3):
            profile = mock_response.profiles.add()
            self._mock_profile(profile)

        profile_id = fuzzy.FuzzyUUID().fuzz()
        mock.instance.register_mock_response(
            'profile',
            'get_peers',
            mock_response,
            profile_id=profile_id,
        )

        response = self.client.call_action('get_categories', profile_id=profile_id)
        self.assertTrue(response.success)
        self.assertEqual(len(response.result.profile_categories), 1)
