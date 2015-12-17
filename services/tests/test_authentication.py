from django.conf import settings
from django.test import (
    Client,
    override_settings,
)

import mock
from service.control import Client as SOAClient
from service_protobufs import soa_pb2

from users.factories import TokenFactory

from ..test import (
    mocks,
    TestCase,
)
from ..authentication import AUTHENTICATION_TOKEN_COOKIE_KEY


class Test(TestCase):

    def setUp(self):
        super(TestCase, self).setUp()
        self.client = Client()

    def _send_request(self, request, **kwargs):
        return self.client.post(
            '/v1/',
            data=request.SerializeToString(),
            content_type='application/x-protobuf',
            **kwargs
        )

    @mock.patch('services.views.import_string')
    def test_unauthenticated_request(self, patched):
        patched_transport = patched()
        patched_transport.process_request.return_value = soa_pb2.ServiceResponseV1()

        soa_client = SOAClient('user')
        request = soa_client._build_request('get_active_devices')
        response = self._send_request(request)

        processed_request = patched_transport.process_request.call_args[0][0]
        self.assertEqual(processed_request.control.token, '')
        self.assertEqual(response.cookies.items(), [])

    @mock.patch('services.views.import_string')
    def test_successful_authentication_sets_cookie(self, patched):
        expected_token = mocks.mock_token()
        patched_transport = patched()
        patched_transport.process_request.return_value = soa_pb2.ServiceResponseV1(
            control=soa_pb2.ControlV1(token=expected_token),
        )
        soa_client = SOAClient('user')
        request = soa_client._build_request('authenticate_user')
        response = self._send_request(request)
        cookie = response.cookies.get(AUTHENTICATION_TOKEN_COOKIE_KEY)
        self.assertTrue(cookie)
        self.assertEqual(cookie.value, expected_token)
        self.assertEqual(cookie.get('domain'), settings.AUTHENTICATION_TOKEN_COOKIE_DOMAIN)
        self.assertEqual(cookie.get('path'), '/')
        self.assertTrue(cookie.get('httponly'))
        self.assertEqual(cookie.get('max-age'), settings.AUTHENTICATION_TOKEN_COOKIE_MAX_AGE)
        self.assertFalse(cookie.get('secure'))

    @override_settings(AUTHENTICATION_TOKEN_COOKIE_SECURE=True)
    @mock.patch('services.views.import_string')
    def test_successful_authentication_sets_cookie_secure(self, patched):
        expected_token = mocks.mock_token()
        patched_transport = patched()
        patched_transport.process_request.return_value = soa_pb2.ServiceResponseV1(
            control=soa_pb2.ControlV1(token=expected_token),
        )
        soa_client = SOAClient('user')
        request = soa_client._build_request('authenticate_user')
        response = self._send_request(request)
        cookie = response.cookies.get(AUTHENTICATION_TOKEN_COOKIE_KEY)
        self.assertTrue(cookie)
        self.assertEqual(cookie.value, expected_token)
        self.assertEqual(cookie.get('domain'), settings.AUTHENTICATION_TOKEN_COOKIE_DOMAIN)
        self.assertEqual(cookie.get('path'), '/')
        self.assertTrue(cookie.get('httponly'))
        self.assertEqual(cookie.get('max-age'), settings.AUTHENTICATION_TOKEN_COOKIE_MAX_AGE)
        self.assertTrue(cookie.get('secure'))

    @mock.patch('services.views.import_string')
    def test_authenticated_request(self, patched):
        token = TokenFactory.create()
        expected_token = mocks.mock_token(auth_token=token.key)
        patched_transport = patched()
        patched_transport.process_request.return_value = soa_pb2.ServiceResponseV1(
            control=soa_pb2.ControlV1(token=expected_token),
        )
        soa_client = SOAClient('user')

        # authenticate the user
        request = soa_client._build_request('authenticate_user')
        self._send_request(request)

        request = soa_client._build_request('get_active_devices')
        self._send_request(request)

        processed_request = patched_transport.process_request.call_args[0][0]
        self.assertEqual(processed_request.control.token, expected_token)

    @mock.patch('services.views.import_string')
    def test_authenticated_request_header(self, patched):
        token = TokenFactory.create()
        expected_token = mocks.mock_token(auth_token=token.key)
        patched_transport = patched()
        patched_transport.process_request.return_value = soa_pb2.ServiceResponseV1(
            control=soa_pb2.ControlV1(token=expected_token),
        )
        soa_client = SOAClient('user')

        request = soa_client._build_request('get_active_devices')
        self._send_request(
            request,
            HTTP_AUTHORIZATION='Token %s' % (expected_token,),
        )
        self.assertEqual(
            patched_transport.process_request.call_args[0][0].control.token,
            expected_token,
        )

    @mock.patch('services.views.import_string')
    def test_authenticated_request_doesnt_set_cookie(self, patched):
        token = TokenFactory.create()
        expected_token = mocks.mock_token(auth_token=token.key)
        patched_transport = patched()
        patched_transport.process_request.return_value = soa_pb2.ServiceResponseV1(
            control=soa_pb2.ControlV1(token=expected_token),
        )
        soa_client = SOAClient('user')

        request = soa_client._build_request('get_active_devices')
        response = self._send_request(
            request,
            HTTP_AUTHORIZATION='Token %s' % (expected_token,),
        )
        self.assertEqual(
            patched_transport.process_request.call_args[0][0].control.token,
            expected_token,
        )
        self.assertIsNone(response.cookies.get(AUTHENTICATION_TOKEN_COOKIE_KEY))

    @mock.patch('services.views.import_string')
    def test_logout_clears_cookie(self, patched):
        token = TokenFactory.create()
        expected_token = mocks.mock_token(auth_token=token.key)
        patched_transport = patched()
        patched_transport.process_request.return_value = soa_pb2.ServiceResponseV1(
            control=soa_pb2.ControlV1(token=expected_token),
        )
        soa_client = SOAClient('user')

        # authenticate the user
        request = soa_client._build_request('authenticate_user')
        self._send_request(request)

        # simulate logout where the token is no longer on the response.control object
        patched_transport.process_request.return_value = soa_pb2.ServiceResponseV1()

        request = soa_client._build_request('logout')
        response = self._send_request(request)
        cookie = response.cookies.get(AUTHENTICATION_TOKEN_COOKIE_KEY)
        self.assertEqual(cookie['expires'], 'Thu, 01-Jan-1970 00:00:00 GMT')
