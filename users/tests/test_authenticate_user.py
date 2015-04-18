import service.control
from mock import patch
from protobufs.services.user.actions import authenticate_user_pb2
from protobufs.services.user import containers_pb2 as user_containers
from services.test import TestCase
from services.token import parse_token

from . import MockCredentials
from .. import (
    factories,
    providers,
)


class TestUsersAuthentication(TestCase):

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
            'authenticate_user',
            backend=0,
            credentials={
                'key': self.user.primary_email,
                'secret': 'password',
            },
        )

    def test_authenticate_user(self):
        response = self._authenticate_user()
        self.assertTrue(response.success)
        self.assertTrue(response.result.token)
        self.assertFalse(response.result.new_user)
        self._verify_containers(response.result.user, self.user)

    def test_authenticate_user_invalid_password(self):
        with self.assertRaises(self.client.CallActionError):
            self.client.call_action(
                'authenticate_user',
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

    @patch.object(providers.OAuth2Credentials, '_refresh')
    @patch('users.providers.verify_id_token')
    @patch.object(providers.Google, '_get_profile')
    @patch('users.providers.credentials_from_code')
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
            'authenticate_user',
            backend=authenticate_user_pb2.RequestV1.GOOGLE,
            credentials={
                'key': 'some-code',
                'secret': 'some-id-token',
            },
        )
        self.assertFalse(response.result.new_user)
        self._verify_containers(
            response.result.user,
            user.to_protobuf(user_containers.UserV1()),
        )

    @patch.object(providers.OAuth2Credentials, '_refresh')
    @patch('users.providers.verify_id_token')
    @patch.object(providers.Google, '_get_profile')
    @patch('users.providers.credentials_from_code')
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
            'authenticate_user',
            backend=authenticate_user_pb2.RequestV1.GOOGLE,
            credentials={
                'key': 'some-code',
                'secret': 'some-id-token',
            },
        )
        self.assertEqual(response.result.user.primary_email, 'mwhahn@gmail.com')
        self.assertTrue(response.result.new_user)
