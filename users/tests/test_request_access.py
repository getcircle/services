import service.control

from services.test import TestCase


class TestRequestAccess(TestCase):

    def setUp(self):
        self.client = service.control.Client('user', token='test-token')

    def test_request_access_missing_arguments(self):
        with self.assertFieldError('anonymous_user', 'MISSING'):
            self.client.call_action('request_access')
