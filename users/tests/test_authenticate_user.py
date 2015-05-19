import service.control
from mock import patch
from protobufs.services.user import containers_pb2 as user_containers
from protobufs.services.user.actions import authenticate_user_pb2
from protobufs.services.user.containers import token_pb2
from services.test import TestCase
from services.token import parse_token

from . import MockCredentials
from .. import (
    factories,
    providers,
)
from ..providers import google as google_provider


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
    def test_get_authentication_instructions_new_user_google_domain(self, mocked_dns):
        self._mock_dns(mocked_dns, is_google=True)
        response = self.client.call_action(
            'get_authentication_instructions',
            email='example@example.com',
        )
        self.assertFalse(response.result.user_exists)
        self.assertTrue(response.result.authorization_url)
        self.assertEqual(response.result.backend, authenticate_user_pb2.RequestV1.GOOGLE)

    @patch('users.actions.DNS.mxlookup')
    def test_get_authentication_instructions_existing_user(self, mocked_dns):
        self._mock_dns(mocked_dns, is_google=True)
        user = factories.UserFactory.create(primary_email='example@example.com')
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
        response = self.client.call_action(
            'get_authentication_instructions',
            email='example@example.com',
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


class TestUsersAuthentication(TestCase):

    action = 'authenticate_user'

    def setUp(self):
        super(TestUsersAuthentication, self).setUp()
        self.client = service.control.Client('user')
        self.user = factories.UserFactory.create_protobuf(password='password')
        self.id_token = {
            'at_hash': 'MfuEK9IFxPzEZpYwqNklfQ',
            'aud': '1077014421904-1a697ks3qvtt6975qfqhmed8529en8s2.apps.googleusercontent.com',
            'azp': '1077014421904-pes3pbf96obmp75kb00qouoiqf18u78h.apps.googleusercontent.com',
            'email': 'mwhahn@gmail.com',
            'email_verified': True,
            'exp': 1423613129,
            'iat': 1423609229,
            'iss': 'accounts.google.com',
            'sub': '100900090880587164138',
        }

    def _authenticate_user(self):
        return self.client.call_action(
            self.action,
            backend=0,
            credentials={
                'key': self.user.primary_email,
                'secret': 'password',
            },
            client_type=token_pb2.IOS,
        )

    def test_authenticate_user(self):
        response = self._authenticate_user()
        self.assertTrue(response.success)
        self.assertTrue(response.result.token)
        self.assertFalse(response.result.new_user)
        self.verify_containers(response.result.user, self.user)

    def test_authenticate_user_invalid_password(self):
        with self.assertRaises(service.control.CallActionError):
            self.client.call_action(
                self.action,
                backend=0,
                credentials={
                    'key': self.user.primary_email,
                    'secret': 'invalid',
                },
            )

    def test_authenticate_user_client_type_required(self):
        with self.assertFieldError('client_type', 'MISSING'):
            self.client.call_action(
                self.action,
                backend=0,
                credentials={
                    'key': self.user.primary_email,
                    'secret': 'invalid',
                },
            )

    def test_authenticate_user_decode_token(self):
        response = self._authenticate_user()
        self.assertTrue(response.success)
        token = parse_token(response.result.token)
        self.assertTrue(token.auth_token)
        self.assertTrue(token.user_id)

    @patch.object(google_provider.OAuth2Credentials, '_refresh')
    @patch('users.providers.google.verify_id_token')
    @patch.object(providers.Google, '_get_profile')
    @patch('users.providers.google.credentials_from_code')
    def test_authenticate_user_google_user_exists(
            self,
            mocked_credentials_from_code,
            mocked_get_profile,
            mocked_verify_id_token,
            *args,
            **kwargs
        ):
        mocked_credentials_from_code.return_value = MockCredentials(self.id_token)
        mocked_get_profile.return_value = {'displayName': 'Michael Hahn'}
        mocked_verify_id_token.return_value = self.id_token
        user = factories.UserFactory.create()
        factories.IdentityFactory.create(
            provider=user_containers.IdentityV1.GOOGLE,
            provider_uid=self.id_token['sub'],
            user=user,
        )
        response = self.client.call_action(
            self.action,
            backend=authenticate_user_pb2.RequestV1.GOOGLE,
            credentials={
                'key': 'some-code',
                'secret': 'some-id-token',
            },
            client_type=token_pb2.IOS,
        )
        self.assertFalse(response.result.new_user)
        self.verify_containers(
            response.result.user,
            user.to_protobuf(user_containers.UserV1()),
        )

    @patch.object(google_provider.OAuth2Credentials, '_refresh')
    @patch('users.providers.google.verify_id_token')
    @patch.object(providers.Google, '_get_profile')
    @patch('users.providers.google.credentials_from_code')
    def test_authenticate_user_google_new_user(
            self,
            mocked_credentials_from_code,
            mocked_get_profile,
            mocked_verify_id_token,
            *args,
            **kwargs
        ):
        mocked_credentials_from_code.return_value = MockCredentials(self.id_token)
        mocked_get_profile.return_value = {'displayName': 'Michael Hahn'}
        mocked_verify_id_token.return_value = self.id_token
        response = self.client.call_action(
            self.action,
            backend=authenticate_user_pb2.RequestV1.GOOGLE,
            credentials={
                'key': 'some-code',
                'secret': 'some-id-token',
            },
            client_type=token_pb2.ANDROID,
        )
        self.assertEqual(response.result.user.primary_email, 'mwhahn@gmail.com')
        self.assertTrue(response.result.new_user)
