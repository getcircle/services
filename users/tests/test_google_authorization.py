import urlparse

import arrow
from django.conf import settings
from mock import (
    MagicMock,
    patch,
)
from oauth2client.client import (
    AccessTokenInfo,
    AccessTokenRefreshError,
    FlowExchangeError,
)
from oauth2client.crypt import AppIdentityError
from protobufs.services.user import containers_pb2 as user_containers
from rest_framework.authtoken.models import Token
import service.control

from services.test import (
    fuzzy,
    mocks,
    TestCase,
)

from . import MockCredentials
from .. import (
    factories,
    models,
    providers,
)
from ..providers import google as google_provider


class TestGoogleAuthorization(TestCase):

    def setUp(self):
        super(TestGoogleAuthorization, self).setUp()
        self.client = service.control.Client('user')
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

    def test_get_authorization_instructions_google(self):
        response = self.client.call_action(
            'get_authorization_instructions',
            provider=user_containers.IdentityV1.GOOGLE,
            login_hint='mwhahn@gmail.com',
        )

        url = urlparse.urlparse(response.result.authorization_url)
        params = dict(urlparse.parse_qsl(url.query))
        self.assertEqual(params['response_type'], 'code')
        self.assertEqual(params['client_id'], settings.GOOGLE_CLIENT_ID)
        self.assertEqual(params['redirect_uri'], settings.GOOGLE_REDIRECT_URI)
        self.assertEqual(params['scope'], settings.GOOGLE_SCOPE.strip())
        self.assertEqual(params['access_type'], 'offline')
        self.assertEqual(params['login_hint'], 'mwhahn@gmail.com')
        state = params['state']
        payload = providers.parse_state_token(user_containers.IdentityV1.GOOGLE, state)
        self.assertTrue(payload['csrftoken'])

    @patch('users.providers.google.verify_id_token')
    @patch.object(providers.Google, '_get_profile')
    @patch('users.providers.google.credentials_from_code')
    def test_complete_authorization_no_user(
            self,
            mocked_credentials_from_code,
            mocked_get_profile,
            mocked_verify_id_token,
        ):
        mocked_credentials_from_code.return_value = MockCredentials(self.id_token)
        mocked_get_profile.return_value = {'displayName': 'Michael Hahn'}
        mocked_verify_id_token.return_value = self.id_token
        response = self.client.call_action(
            'complete_authorization',
            provider=user_containers.IdentityV1.GOOGLE,
            oauth_sdk_details={
                'code': 'some-code',
                'id_token': 'id-token',
            },
        )
        self.assertEqual(response.result.identity.provider, user_containers.IdentityV1.GOOGLE)
        self.assertEqual(response.result.identity.full_name, 'Michael Hahn')
        self.assertEqual(response.result.identity.email, 'mwhahn@gmail.com')
        self.assertEqual(response.result.identity.user_id, response.result.user.id)
        self.assertTrue(response.result.new_user)

    @patch.object(providers.Google, '_get_profile')
    @patch('users.providers.google.credentials_from_code')
    def test_complete_authorization_no_user_oauth2_details(
            self,
            mocked_credentials_from_code,
            mocked_get_profile,
        ):
        mocked_credentials_from_code.return_value = MockCredentials(self.id_token)
        mocked_get_profile.return_value = {'displayName': 'Michael Hahn'}
        response = self.client.call_action(
            'complete_authorization',
            provider=user_containers.IdentityV1.GOOGLE,
            oauth2_details={
                'code': 'some-code',
                'state': 'some-state',
            },
        )
        self.assertEqual(response.result.identity.provider, user_containers.IdentityV1.GOOGLE)
        self.assertEqual(response.result.identity.full_name, 'Michael Hahn')
        self.assertEqual(response.result.identity.email, 'mwhahn@gmail.com')
        self.assertEqual(response.result.identity.user_id, response.result.user.id)
        self.assertTrue(response.result.new_user)
        self.assertEqual(response.result.oauth_sdk_details.code, 'some-code')
        self.assertEqual(response.result.oauth_sdk_details.id_token, str(self.id_token))

    @patch.object(google_provider.OAuth2Credentials, 'get_access_token')
    @patch('users.providers.google.verify_id_token')
    @patch.object(providers.Google, '_get_profile')
    def test_complete_authorization_user_exists(
            self,
            mocked_get_profile,
            mocked_verify_id_token,
            mocked_get_access_token,
        ):
        mocked_get_profile.return_value = {'displayName': 'Michael Hahn'}
        mocked_verify_id_token.return_value = self.id_token
        user = factories.UserFactory.create()
        identity = factories.IdentityFactory.create(
            user=user,
            provider_uid=self.id_token['sub'],
            provider=user_containers.IdentityV1.GOOGLE,
        )
        mocked_get_access_token.return_value = AccessTokenInfo(
            access_token=identity.access_token,
            expires_in=4333,
        )
        response = self.client.call_action(
            'complete_authorization',
            provider=user_containers.IdentityV1.GOOGLE,
            oauth_sdk_details={
                'code': 'some-code',
                'id_token': 'id-token',
            },
        )
        self.assertEqual(response.result.identity.provider, user_containers.IdentityV1.GOOGLE)
        self.assertEqual(response.result.identity.full_name, 'Michael Hahn')
        self.assertEqual(response.result.identity.email, identity.email)
        self.assertEqual(response.result.identity.user_id, response.result.user.id)
        self.assertEqual(response.result.identity.access_token, identity.access_token)
        self.assertFalse(response.result.new_user)

    @patch('users.providers.google.verify_id_token')
    @patch.object(providers.Google, '_get_profile')
    @patch('users.providers.google.credentials_from_code')
    def test_complete_authorization_flow_exchange_error(
            self,
            mocked_credentials_from_code,
            mocked_get_profile,
            mocked_verify_id_token,
        ):
        mocked_credentials_from_code.side_effect = FlowExchangeError
        mocked_get_profile.return_value = {'displayName': 'Michael Hahn'}
        mocked_verify_id_token.return_value = self.id_token
        with self.assertRaisesCallActionError() as expected:
            self.client.call_action(
                'complete_authorization',
                provider=user_containers.IdentityV1.GOOGLE,
                oauth_sdk_details={
                    'code': 'some-code',
                    'id_token': 'id-token',
                },
            )

        self.assertIn('PROVIDER_API_ERROR', expected.exception.response.errors)

    @patch('users.providers.google.verify_id_token')
    @patch.object(providers.Google, '_get_profile')
    @patch('users.providers.google.credentials_from_code')
    def test_complete_authorization_incomplete_profile(
            self,
            mocked_credentials_from_code,
            mocked_get_profile,
            mocked_verify_id_token,
        ):
        mocked_credentials_from_code.return_value = MockCredentials(self.id_token)
        mocked_get_profile.return_value = {}
        mocked_verify_id_token.return_value = self.id_token
        with self.assertRaisesCallActionError() as expected:
            self.client.call_action(
                'complete_authorization',
                provider=user_containers.IdentityV1.GOOGLE,
                oauth_sdk_details={
                    'code': 'some-code',
                    'id_token': 'id-token',
                },
            )

        self.assertIn('PROVIDER_PROFILE_FIELD_MISSING', expected.exception.response.errors)

    @patch.object(google_provider.OAuth2Credentials, '_refresh')
    @patch('users.providers.google.verify_id_token')
    @patch.object(providers.Google, '_get_profile')
    def test_complete_authorization_expired_access_token(
            self,
            mocked_get_profile,
            mocked_verify_id_token,
            mocked_refresh,
        ):
        mocked_get_profile.return_value = {'displayName': 'Michael Hahn'}
        mocked_verify_id_token.return_value = self.id_token
        user = factories.UserFactory.create()
        identity = factories.IdentityFactory.create(
            user=user,
            provider_uid=self.id_token['sub'],
            provider=user_containers.IdentityV1.GOOGLE,
            expires_at=arrow.utcnow().replace(days=-2).timestamp,
        )
        response = self.client.call_action(
            'complete_authorization',
            provider=user_containers.IdentityV1.GOOGLE,
            oauth_sdk_details={
                'code': 'some-code',
                'id_token': 'id-token',
            },
        )
        self.assertEqual(response.result.identity.provider, user_containers.IdentityV1.GOOGLE)
        self.assertEqual(response.result.identity.full_name, 'Michael Hahn')
        self.assertEqual(response.result.identity.email, identity.email)
        self.assertEqual(response.result.identity.user_id, response.result.user.id)
        self.assertEqual(response.result.identity.access_token, identity.access_token)
        self.assertEqual(mocked_refresh.call_count, 1)

    @patch('users.providers.google.verify_id_token')
    @patch.object(providers.Google, '_get_profile')
    def test_complete_authorization_verify_id_token_error(
            self,
            mocked_get_profile,
            mocked_verify_id_token,
        ):
        mocked_get_profile.return_value = {'displayName': 'Michael Hahn'}
        mocked_verify_id_token.side_effect = AppIdentityError
        with self.assertRaisesCallActionError() as expected:
            self.client.call_action(
                'complete_authorization',
                provider=user_containers.IdentityV1.GOOGLE,
                oauth_sdk_details={
                    'code': 'some-code',
                    'id_token': 'id-token',
                },
            )

        self.assertIn('FIELD_ERROR', expected.exception.response.errors)
        field_error = expected.exception.response.error_details[0]
        self.assertEqual(field_error.key, 'oauth_sdk_details.id_token')
        self.assertEqual(field_error.detail, 'INVALID')

    @patch.object(google_provider.OAuth2Credentials, 'get_access_token')
    @patch('users.providers.google.verify_id_token')
    @patch.object(providers.Google, '_get_profile')
    @patch.object(providers.Google, '_get_credentials_from_code')
    def test_complete_authorization_expired_access_tokens(
            self,
            mocked_credentials_from_code,
            mocked_get_profile,
            mocked_verify_id_token,
            mocked_get_access_token,
        ):
        mocked_credentials_from_code().get_access_token.side_effect = AccessTokenRefreshError
        mocked_get_access_token.side_effect = AccessTokenRefreshError
        mocked_get_profile.return_value = {'displayName': 'Michael Hahn'}
        mocked_verify_id_token.return_value = self.id_token
        user = factories.UserFactory.create()
        factories.IdentityFactory.create(
            user=user,
            provider_uid=self.id_token['sub'],
            provider=user_containers.IdentityV1.GOOGLE,
        )
        with self.assertRaisesCallActionError() as expected:
            self.client.call_action(
                'complete_authorization',
                provider=user_containers.IdentityV1.GOOGLE,
                oauth_sdk_details={
                    'code': 'some-code',
                    'id_token': 'id-token',
                },
            )

        self.assertIn('TOKEN_EXPIRED', expected.exception.response.errors)

    @patch.object(providers.Google, '_get_credentials_from_code')
    @patch.object(google_provider.OAuth2Credentials, 'refresh')
    @patch.object(google_provider.OAuth2Credentials, 'get_access_token')
    @patch('users.providers.google.verify_id_token')
    @patch.object(providers.Google, '_get_profile')
    def test_complete_authorization_token_revoked(
            self,
            mocked_get_profile,
            mocked_verify_id_token,
            mocked_get_access_token,
            mocked_refresh,
            mocked_get_credentials_from_code,
        ):
        mock_response = MagicMock()
        type(mock_response).status_code = 401
        mocked_get_profile.side_effect = [
            providers.ExchangeError(mock_response),
            {'displayName': 'Michael Hahn'},
        ]
        mocked_verify_id_token.return_value = self.id_token
        mocked_refresh.side_effect = AccessTokenRefreshError
        mocked_get_credentials_from_code.return_value = MockCredentials(self.id_token)
        user = factories.UserFactory.create()
        identity = factories.IdentityFactory.create(
            user=user,
            provider_uid=self.id_token['sub'],
            provider=user_containers.IdentityV1.GOOGLE,
        )
        mocked_get_access_token.return_value = AccessTokenInfo(
            access_token=identity.access_token,
            expires_in=4333,
        )
        response = self.client.call_action(
            'complete_authorization',
            provider=user_containers.IdentityV1.GOOGLE,
            oauth_sdk_details={
                'code': 'some-code',
                'id_token': 'id-token',
            },
        )
        self.assertEqual(response.result.identity.provider, user_containers.IdentityV1.GOOGLE)
        self.assertEqual(response.result.identity.full_name, 'Michael Hahn')
        self.assertEqual(response.result.identity.email, identity.email)
        self.assertEqual(response.result.identity.user_id, response.result.user.id)
        self.assertEqual(mocked_get_credentials_from_code.call_count, 1)

    @patch.object(google_provider.OAuth2Credentials, 'get_access_token')
    @patch('users.providers.google.verify_id_token')
    @patch.object(providers.Google, '_get_profile')
    @patch('users.providers.google.credentials_from_code')
    def test_complete_authorization_user_exists_no_identity(
            self,
            mocked_credentials_from_code,
            mocked_get_profile,
            mocked_verify_id_token,
            mocked_get_access_token,
        ):
        mocked_credentials_from_code.return_value = MockCredentials(self.id_token)
        mocked_get_profile.return_value = {'displayName': 'Michael Hahn'}
        mocked_verify_id_token.return_value = self.id_token
        factories.UserFactory.create(primary_email='mwhahn@gmail.com')
        mocked_get_access_token.return_value = AccessTokenInfo(
            access_token=fuzzy.FuzzyUUID().fuzz(),
            expires_in=4333,
        )
        response = self.client.call_action(
            'complete_authorization',
            provider=user_containers.IdentityV1.GOOGLE,
            oauth_sdk_details={
                'code': 'some-code',
                'id_token': 'id-token',
            },
        )
        self.assertEqual(response.result.identity.provider, user_containers.IdentityV1.GOOGLE)
        self.assertEqual(response.result.identity.full_name, 'Michael Hahn')
        self.assertEqual(response.result.identity.user_id, response.result.user.id)

    @patch('users.providers.google.requests')
    def test_google_revoke(self, patched_requests):
        user = factories.UserFactory.create()
        identity = factories.IdentityFactory.create_protobuf(
            user=user,
            provider_uid=self.id_token['sub'],
            provider=user_containers.IdentityV1.GOOGLE,
        )
        token = Token.objects.create(user=user)
        client = service.control.Client('user', token=mocks.mock_token(user_id=user.id))
        client.call_action('delete_identity', identity=identity)

        with self.assertRaises(models.User.DoesNotExist):
            models.User.objects.get(id=identity.id)

        with self.assertRaises(Token.DoesNotExist):
            Token.objects.get(user=token.user)

    @patch('users.providers.google.requests')
    def test_google_revoke_provider_api_error(self, patched_requests):
        type(patched_requests.get()).ok = False
        type(patched_requests.get()).reason = 'Failure'
        user = factories.UserFactory.create()
        identity = factories.IdentityFactory.create_protobuf(
            user=user,
            provider_uid=self.id_token['sub'],
            provider=user_containers.IdentityV1.GOOGLE,
        )
        client = service.control.Client('user', token=mocks.mock_token(user_id=user.id))
        with self.assertRaisesCallActionError() as expected:
            client.call_action('delete_identity', identity=identity)
        self.assertIn('PROVIDER_API_ERROR', expected.exception.response.errors)
