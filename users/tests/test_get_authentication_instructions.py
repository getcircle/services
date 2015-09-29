import urlparse

import service.control
from mock import patch
from protobufs.services.user.actions import authenticate_user_pb2
from protobufs.services.user import containers_pb2 as user_containers
from services.test import (
    mocks,
    TestCase,
)

from .. import factories
from ..providers.base import parse_state_token


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
        with self.assertRaisesCallActionError() as expected:
            self.client.call_action('get_authentication_instructions')
        self.assertIn('MISSING_REQUIRED_PARAMETERS', expected.exception.response.errors)

    def test_get_authentication_instructions_email_invalid(self):
        with self.assertFieldError('email'):
            self.client.call_action('get_authentication_instructions', email='invalid@invalid')

    def test_get_authentication_instructions_organization_domain_no_sso(self):
        response = self.client.call_action(
            'get_authentication_instructions',
            organization_domain='doesnotexist',
        )
        # should default to internal backend since we don't have any sso setup
        self.assertEqual(response.result.backend, authenticate_user_pb2.RequestV1.INTERNAL)

    def test_get_authentication_instructions_organization_sso_organization_domain(self):
        with self.mock_transport() as mock:
            mock.instance.dont_mock_service('user')
            mock.instance.register_mock_object(
                service='organization',
                action='get_sso_metadata',
                return_object_path='sso',
                return_object=mocks.mock_sso(),
                organization_domain='example',
            )
            mock.instance.register_mock_object(
                service='organization',
                action='get_organization',
                return_object_path='organization',
                return_object=mocks.mock_organization(
                    domain='example',
                    name='Example',
                    image_url='imageurl',
                ),
                domain='example',
            )
            response = self.client.call_action(
                'get_authentication_instructions',
                organization_domain='example',
            )

        self.assertTrue(response.result.authorization_url)
        self.assertEqual(response.result.backend, authenticate_user_pb2.RequestV1.OKTA)
        self.assertTrue(response.result.provider_name, 'Okta')

    def test_get_authentication_instructions_organization_domain(self):
        with self.mock_transport() as mock:
            mock.instance.dont_mock_service('user')
            mock.instance.register_mock_object(
                service='organization',
                action='get_sso_metadata',
                return_object_path='sso',
                return_object=mocks.mock_sso(),
                organization_domain='example',
            )
            mock.instance.register_mock_object(
                service='organization',
                action='get_organization',
                return_object_path='organization',
                return_object=mocks.mock_organization(
                    domain='example',
                    name='Example',
                    image_url='imageurl',
                ),
                domain='example',
            )
            response = self.client.call_action(
                'get_authentication_instructions',
                organization_domain='example',
            )

        self.assertEqual(response.result.organization_image_url, 'imageurl')

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
            mock.instance.register_mock_object(
                service='organization',
                action='get_organization',
                return_object_path='organization',
                return_object=mocks.mock_organization(
                    domain='example',
                    name='Example',
                    image_url='imageurl',
                ),
                domain='example',
            )
            response = self.client.call_action('get_authentication_instructions', email=email)

        self.assertTrue(response.result.authorization_url)
        self.assertEqual(response.result.backend, authenticate_user_pb2.RequestV1.OKTA)

    @patch('users.actions.DNS.mxlookup')
    def test_get_authentication_instructions_organization_sso_force_internal(self, mocked_dns):
        self._mock_dns(mocked_dns, is_google=True)
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
            mock.instance.register_mock_object(
                service='organization',
                action='get_organization',
                return_object_path='organization',
                return_object=mocks.mock_organization(
                    domain='example',
                    name='Example',
                    image_url='imageurl',
                ),
                domain='example',
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
            USER_SERVICE_ALLOWED_REDIRECT_URIS_REGEX_WHITELIST=(
                '^(https?://)?(\w+\.)?lunohq\.com/auth',
            ),
        ):
            response = self.client.call_action(
                'get_authentication_instructions',
                email=email,
                redirect_uri='https://frontend.lunohq.com/auth',
            )
        parsed_url = urlparse.urlparse(response.result.authorization_url)
        query = dict(urlparse.parse_qsl(parsed_url.query))
        parsed_state = parse_state_token(user_containers.IdentityV1.GOOGLE, query['state'])
        self.assertIn('frontend.lunohq', parsed_state['redirect_uri'])
        self.assertFalse(response.result.user_exists)
        self.assertTrue(response.result.authorization_url)
        self.assertEqual(response.result.backend, authenticate_user_pb2.RequestV1.GOOGLE)

    @patch('users.actions.DNS.mxlookup')
    def test_get_authentication_instructions_redirect_uri_invalid(self, mocked_dns):
        self._mock_dns(mocked_dns, is_google=True)
        email = 'example@example.com'
        with self.settings(USER_SERVICE_FORCE_GOOGLE_AUTH=(email,)), self.assertFieldError(
            'redirect_uri'
        ):
            self.client.call_action(
                'get_authentication_instructions',
                email=email,
                redirect_uri='https://frontendlunohq.com/auth/success/',
            )

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
