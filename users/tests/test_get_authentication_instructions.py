import service.control
from mock import patch
from protobufs.services.user.actions import authenticate_user_pb2
from protobufs.services.user.containers import token_pb2
from services.test import (
    mocks,
    TestCase,
)

from .. import factories


class TestUsersGetAuthenticationInstructions(TestCase):

    def setUp(self):
        super(TestUsersGetAuthenticationInstructions, self).setUp()
        self.client = service.control.Client('user')

    def _mock_dns(self, mock_dns, is_google):
        if is_google:
            mock_dns.return_value = [(10, 'gmail-smtp.google.com')]
        else:
            mock_dns.return_value = [(10, 'yahoo-smtp.yahoo.com')]

    def test_get_authentication_instructions_email_required(self):
        with self.assertFieldError('email', 'MISSING'):
            self.client.call_action('get_authentication_instructions')

    def test_get_authentication_instructions_email_invalid(self):
        with self.assertFieldError('email'):
            self.client.call_action('get_authentication_instructions', email='invalid@invalid')

    @patch('users.actions.DNS.mxlookup')
    def test_get_authentication_instructions_organization_sso(self, mocked_dns):
        self._mock_dns(mocked_dns, is_google=True)
        email = 'example@example.com'
        with self.mock_transport() as mock:
            mock.instance.dont_mock_service('user')
            mock.instance.register_mock_object(
                service='organization',
                action='get_sso_metadata',
                return_object_path='sso',
                return_object=mocks.mock_sso(),
                organization_domain='example',
            )
            response = self.client.call_action(
                'get_authentication_instructions',
                email=email,
                client_type=token_pb2.WEB,
            )

        self.assertTrue(response.result.authorization_url)
        self.assertEqual(response.result.backend, authenticate_user_pb2.RequestV1.SAML)

    @patch('users.actions.DNS.mxlookup')
    def test_get_authentication_instructions_organization_sso_force_internal(self, mocked_dns):
        self._mock_dns(mocked_dns, is_google=False)
        email = 'example@example.com'
        with self.mock_transport() as mock, self.settings(
            USER_SERVICE_FORCE_DOMAIN_INTERNAL_AUTH=('example',)
        ):
            mock.instance.register_mock_object(
                service='organization',
                action='get_sso_metadata',
                return_object_path='sso',
                return_object=mocks.mock_sso(),
                organization_domain='example',
            )
            response = self.client.call_action(
                'get_authentication_instructions',
                email=email,
            )
        self.assertFalse(response.result.authorization_url)
        self.assertEqual(response.result.backend, authenticate_user_pb2.RequestV1.INTERNAL)

    @patch('users.actions.DNS.mxlookup')
    def test_get_authentication_instructions_new_user_google_domain(self, mocked_dns):
        self._mock_dns(mocked_dns, is_google=True)
        email = 'example@example.com'
        with self.settings(USER_SERVICE_FORCE_GOOGLE_AUTH=(email,)):
            response = self.client.call_action(
                'get_authentication_instructions',
                email=email,
            )
        self.assertFalse(response.result.user_exists)
        self.assertTrue(response.result.authorization_url)
        self.assertEqual(response.result.backend, authenticate_user_pb2.RequestV1.GOOGLE)

    @patch('users.actions.DNS.mxlookup')
    def test_get_authentication_instructions_redirect_uri(self, mocked_dns):
        self._mock_dns(mocked_dns, is_google=True)
        email = 'example@example.com'
        with self.settings(
            USER_SERVICE_FORCE_GOOGLE_AUTH=(email,),
            USER_SERVICE_ALLOWED_REDIRECT_URIS=('https://frontendlunohq.com/auth/success/',),
        ):
            response = self.client.call_action(
                'get_authentication_instructions',
                email=email,
                redirect_uri='https://frontendlunohq.com/auth/success/',
            )
        self.assertFalse(response.result.user_exists)
        self.assertTrue(response.result.authorization_url)
        self.assertIn('frontendlunohq', response.result.authorization_url)
        self.assertEqual(response.result.backend, authenticate_user_pb2.RequestV1.GOOGLE)

    @patch('users.actions.DNS.mxlookup')
    def test_get_authentication_instructions_redirect_uri_invalid(self, mocked_dns):
        self._mock_dns(mocked_dns, is_google=True)
        email = 'example@example.com'
        with self.settings(USER_SERVICE_FORCE_GOOGLE_AUTH=(email,)):
            response = self.client.call_action(
                'get_authentication_instructions',
                email=email,
                redirect_uri='https://frontendlunohq.com/auth/success/',
            )
        self.assertFalse(response.result.user_exists)
        self.assertTrue(response.result.authorization_url)
        self.assertNotIn('frontendlunohq', response.result.authorization_url)
        self.assertEqual(response.result.backend, authenticate_user_pb2.RequestV1.GOOGLE)

    @patch('users.actions.DNS.mxlookup')
    def test_get_authentication_instructions_existing_user(self, mocked_dns):
        self._mock_dns(mocked_dns, is_google=True)
        user = factories.UserFactory.create(primary_email='example@example.com')
        with self.settings(USER_SERVICE_FORCE_GOOGLE_AUTH=(user.primary_email,)):
            response = self.client.call_action(
                'get_authentication_instructions',
                email=user.primary_email,
            )
        self.assertTrue(response.result.user_exists)
        self.assertTrue(response.result.authorization_url)
        self.assertEqual(response.result.backend, authenticate_user_pb2.RequestV1.GOOGLE)

    @patch('users.actions.DNS.mxlookup')
    def test_get_authentication_instructions_new_user_non_google_domain(self, mocked_dns):
        self._mock_dns(mocked_dns, is_google=False)
        email = 'example@example.com'
        with self.settings(USER_SERVICE_FORCE_GOOGLE_AUTH=(email,)):
            response = self.client.call_action(
                'get_authentication_instructions',
                email=email,
            )
        self.assertFalse(response.result.user_exists)
        self.assertFalse(response.result.authorization_url)
        self.assertEqual(response.result.backend, authenticate_user_pb2.RequestV1.INTERNAL)

    @patch('users.actions.DNS.mxlookup')
    def test_get_authentication_instructions_existing_user_non_google_domain(self, mocked_dns):
        self._mock_dns(mocked_dns, is_google=False)
        user = factories.UserFactory.create(primary_email='example@example.com')
        response = self.client.call_action(
            'get_authentication_instructions',
            email=user.primary_email,
        )
        self.assertTrue(response.result.user_exists)
        self.assertFalse(response.result.authorization_url)
        self.assertEqual(response.result.backend, authenticate_user_pb2.RequestV1.INTERNAL)

    @patch('users.actions.DNS.mxlookup')
    def test_get_authentication_instructions_google_domain_force_to_password(self, mocked_dns):
        self._mock_dns(mocked_dns, is_google=True)
        user = factories.UserFactory.create(primary_email='demo@circlehq.co')
        with self.settings(USER_SERVICE_FORCE_INTERNAL_AUTH=(user.primary_email,)):
            response = self.client.call_action(
                'get_authentication_instructions',
                email=user.primary_email,
            )
        self.assertTrue(response.result.user_exists)
        self.assertFalse(response.result.authorization_url)
        self.assertEqual(response.result.backend, authenticate_user_pb2.RequestV1.INTERNAL)
