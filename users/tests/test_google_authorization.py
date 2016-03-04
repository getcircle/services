import urlparse

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
from protobufs.services.organization.containers import sso_pb2
from protobufs.services.user import containers_pb2 as user_containers
from protobufs.services.user.containers import token_pb2
import service.control

from services.test import (
    fuzzy,
    mocks,
    MockedTestCase,
)
from services.token import make_admin_token

from . import MockCredentials
from .. import (
    factories,
    models,
    providers,
)
from ..actions import get_authorization_instructions
from ..providers import google as google_provider
from ..providers.base import get_state_token


class Test(MockedTestCase):

    def setUp(self):
        super(Test, self).setUp()
        self.client = service.control.Client('user')
        self.organization = mocks.mock_organization()
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
            'hd': '%s.com' % (self.organization.domain,),
        }
        token = make_admin_token(organization_id=self.organization.id)
        self.authenticated_client = service.control.Client('user', token=token)
        self.mock.instance.dont_mock_service('user')
        self._setup_google_sso()

    def _setup_google_sso(self):
        self.mock.instance.register_mock_object(
            service='organization',
            action='get_sso',
            return_object_path='sso',
            return_object=mocks.mock_sso(
                saml=None,
                google=sso_pb2.GoogleDetailsV1(domains=['%s.com' % (self.organization.domain,)]),
                provider=sso_pb2.GOOGLE,
                organization_id=self.organization.id,
            ),
            organization_domain=self.organization.domain,
        )

    def _get_state(self):
        return get_state_token(google_provider.Provider.type, {'domain': self.organization.domain})

    def _mock_user_info(self, **overrides):
        defaults = {
            'name': 'Michael Hahn',
            'picture': 'https://smoething.com',
        }
        defaults.update(overrides)

        remove = []
        for key, value in defaults.iteritems():
            if value is None:
                remove.append(key)

        for key in remove:
            defaults.pop(key)

        return defaults

    def test_get_authorization_instructions_google(self):
        authorization_url, provider_name = get_authorization_instructions(
            provider=user_containers.IdentityV1.GOOGLE,
            organization=self.organization,
            login_hint='mwhahn@gmail.com',
        )

        url = urlparse.urlparse(authorization_url)
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

    @patch('users.providers.google.get_user_info')
    @patch('users.providers.google.credentials_from_code')
    def test_complete_authorization(
            self,
            mocked_credentials_from_code,
            mock_user_info,
        ):

        mocked_credentials_from_code.return_value = MockCredentials(self.id_token)
        mock_user_info.return_value = self._mock_user_info()
        response = self.client.call_action(
            'complete_authorization',
            provider=user_containers.IdentityV1.GOOGLE,
            oauth2_details={
                'code': 'some-code',
                'state': self._get_state(),
            },
            client_type=token_pb2.WEB,
        )
        self.assertEqual(response.result.identity.provider, user_containers.IdentityV1.GOOGLE)
        self.assertEqual(response.result.identity.full_name, 'Michael Hahn')
        self.assertEqual(response.result.identity.email, 'mwhahn@gmail.com')
        self.assertEqual(response.result.identity.user_id, response.result.user.id)

    @patch('users.providers.google.get_user_info')
    @patch('users.providers.google.credentials_from_code')
    def test_complete_authorization_no_user(
            self,
            mocked_credentials_from_code,
            mock_user_info,
        ):
        mocked_credentials_from_code.return_value = MockCredentials(self.id_token)
        mock_user_info.return_value = self._mock_user_info()
        response = self.client.call_action(
            'complete_authorization',
            provider=user_containers.IdentityV1.GOOGLE,
            oauth2_details={
                'code': 'some-code',
                'state': self._get_state(),
            },
            client_type=token_pb2.WEB,
        )
        self.assertEqual(response.result.identity.provider, user_containers.IdentityV1.GOOGLE)
        self.assertEqual(response.result.identity.full_name, 'Michael Hahn')
        self.assertEqual(response.result.identity.email, 'mwhahn@gmail.com')
        self.assertEqual(response.result.identity.user_id, response.result.user.id)
        self.assertEqual(response.result.google_credentials.code, 'some-code')
        self.assertEqual(response.result.google_credentials.id_token, str(self.id_token))
        call_args = mocked_credentials_from_code.call_args[1]
        self.assertEqual(call_args['redirect_uri'], settings.GOOGLE_REDIRECT_URI)

        # verify image_url was passed to the create_profile call
        mock_create_profile = self.mock.instance.mocked_calls[1]
        self.assertIn('image_url', mock_create_profile['params']['profile'])

    @patch.object(google_provider.OAuth2Credentials, 'get_access_token')
    @patch('users.providers.google.get_user_info')
    @patch('users.providers.google.credentials_from_code')
    def test_complete_authorization_user_exists(
            self,
            mocked_credentials_from_code,
            mock_user_info,
            mocked_get_access_token,
        ):
        mocked_credentials_from_code.return_value = MockCredentials(self.id_token)
        mock_user_info.return_value = self._mock_user_info()
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
            oauth2_details={
                'code': 'some-code',
                'state': self._get_state(),
            },
            client_type=token_pb2.WEB,
        )
        self.assertEqual(response.result.identity.provider, user_containers.IdentityV1.GOOGLE)
        self.assertEqual(response.result.identity.full_name, 'Michael Hahn')
        self.assertEqual(response.result.identity.email, 'mwhahn@gmail.com')
        self.assertEqual(response.result.identity.user_id, response.result.user.id)

    @patch('users.providers.google.get_user_info')
    @patch('users.providers.google.credentials_from_code')
    def test_complete_authorization_flow_exchange_error(
            self,
            mocked_credentials_from_code,
            mock_user_info,
        ):
        mocked_credentials_from_code.side_effect = FlowExchangeError
        mock_user_info.return_value = self._mock_user_info()
        with self.assertRaisesCallActionError() as expected:
            self.client.call_action(
                'complete_authorization',
                provider=user_containers.IdentityV1.GOOGLE,
                oauth2_details={
                    'code': 'some-code',
                    'state': self._get_state(),
                },
                client_type=token_pb2.WEB,
            )

        self.assertIn('PROVIDER_API_ERROR', expected.exception.response.errors)

    @patch('users.providers.google.get_user_info')
    @patch('users.providers.google.credentials_from_code')
    def test_complete_authorization_incomplete_profile(
            self,
            mocked_credentials_from_code,
            mock_user_info,
        ):
        mocked_credentials_from_code.return_value = MockCredentials(self.id_token)
        mock_user_info.return_value = self._mock_user_info(name=None)
        with self.assertRaisesCallActionError() as expected:
            self.client.call_action(
                'complete_authorization',
                provider=user_containers.IdentityV1.GOOGLE,
                oauth2_details={
                    'code': 'some-code',
                    'state': self._get_state(),
                },
                client_type=token_pb2.WEB,
            )

        self.assertIn('PROVIDER_PROFILE_FIELD_MISSING', expected.exception.response.errors)

    @patch('users.providers.google.get_user_info')
    @patch('users.providers.google.credentials_from_code')
    def test_complete_authorization_unverified_domain(
            self,
            mocked_credentials_from_code,
            mock_user_info,
        ):
        self.id_token['hd'] = 'unverified'
        mocked_credentials_from_code.return_value = MockCredentials(self.id_token)
        mock_user_info.return_value = self._mock_user_info()
        with self.assertRaisesCallActionError() as expected:
            self.client.call_action(
                'complete_authorization',
                provider=user_containers.IdentityV1.GOOGLE,
                oauth2_details={
                    'code': 'some-code',
                    'state': self._get_state(),
                },
                client_type=token_pb2.WEB,
            )

        self.assertIn('INVALID_DOMAIN', expected.exception.response.errors)

    @patch.object(google_provider.OAuth2Credentials, 'get_access_token')
    @patch('users.providers.google.get_user_info')
    @patch('users.providers.google.credentials_from_code')
    def test_complete_authorization_user_exists_no_identity(
            self,
            mocked_credentials_from_code,
            mock_user_info,
            mocked_get_access_token,
        ):
        mocked_credentials_from_code.return_value = MockCredentials(self.id_token)
        mock_user_info.return_value = self._mock_user_info()
        factories.UserFactory.create(primary_email='mwhahn@gmail.com')
        mocked_get_access_token.return_value = AccessTokenInfo(
            access_token=fuzzy.FuzzyUUID().fuzz(),
            expires_in=4333,
        )
        response = self.client.call_action(
            'complete_authorization',
            provider=user_containers.IdentityV1.GOOGLE,
            oauth2_details={
                'code': 'some-code',
                'state': self._get_state(),
            },
            client_type=token_pb2.WEB,
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
        # create tokens for several platforms
        token = models.Token.objects.create(
            user=user,
            client_type=token_pb2.IOS,
            organization_id=self.organization.id,
        )
        models.Token.objects.create(
            user=user,
            client_type=token_pb2.ANDROID,
            organization_id=self.organization.id,
        )

        self.assertEqual(models.Token.objects.filter(user=token.user).count(), 2)
        client = service.control.Client('user', token=mocks.mock_token(user_id=user.id))
        client.call_action('delete_identity', identity=identity)

        with self.assertRaises(models.User.DoesNotExist):
            models.User.objects.get(id=identity.id)

        self.assertEqual(models.Token.objects.filter(user=token.user).count(), 0)

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
