import service.control
from mock import patch
from protobufs.services.user import containers_pb2 as user_containers
from protobufs.services.user.actions import authenticate_user_pb2
from protobufs.services.user.containers import token_pb2

from services.test import (
    mocks,
    MockedTestCase,
)
from services.token import parse_token

from . import MockCredentials
from .. import (
    factories,
    models,
    providers,
)
from ..providers import (
    google as google_provider,
    okta as okta_provider,
)


class Test(MockedTestCase):

    def setUp(self):
        super(Test, self).setUp()
        self.client = service.control.Client('user')
        self.organization = mocks.mock_organization()
        self.user = factories.UserFactory.create_protobuf(
            password='password',
            organization_id=self.organization.id,
        )
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
        self.mock.instance.dont_mock_service('user')

    def _mock_get_organization(self, organization=None):
        organization = organization or self.organization
        self.mock.instance.register_mock_object(
            service='organization',
            action='get_organization',
            return_object_path='organization',
            return_object=self.organization,
            domain=organization.domain,
        )

    def _authenticate_user(self, domain=None):
        domain = domain or self.organization.domain
        return self.client.call_action(
            'authenticate_user',
            backend=0,
            credentials={
                'key': self.user.primary_email,
                'secret': 'password',
            },
            client_type=token_pb2.IOS,
            organization_domain=domain,
        )

    def test_authenticate_user_organization_domain_required(self):
        with self.assertFieldError('organization_domain', 'MISSING'):
            self.client.call_action(
                'authenticate_user',
                backend=0,
                credentials={'key': 'something', 'secret': 'secret'},
            )

    def test_authenticate_user_organization_does_not_exist(self):
        error = self.mock.get_mockable_call_action_error(
            service='organization',
            action='get_organization',
            errors=['FIELD_ERROR'],
            error_details=[{
                'key': 'domain',
                'detail': 'DOES_NOT_EXIST',
                'error': 'FIELD_ERROR',
            }],
        )
        self.mock.instance.register_mock_error(
            service='organization',
            action='get_organization',
            error=error,
            domain='doesnotexist',
        )
        with self.assertFieldError('organization_domain', 'DOES_NOT_EXIST'):
            self._authenticate_user(domain='doesnotexist')

    def test_authenticate_user(self):
        # create a user with a duplicate email since we scope by organization_id
        factories.UserFactory.create(primary_email=self.user.primary_email)
        self._mock_get_organization()

        response = self._authenticate_user()
        self.assertEqual(response.service_response.control.token, response.result.token)
        self.assertTrue(response.success)
        self.assertTrue(response.result.token)
        self.assertFalse(response.result.new_user)
        self.verify_containers(response.result.user, self.user)
        old = models.User.objects.get(pk=response.result.user.id)
        self._authenticate_user()
        new = models.User.objects.get(pk=response.result.user.id)
        self.assertTrue(old.last_login)
        self.assertTrue(new.last_login)
        self.assertNotEqual(old.last_login, new.last_login)

    def test_authenticate_user_invalid_password(self):
        with self.assertRaises(service.control.CallActionError):
            self.client.call_action(
                'authenticate_user',
                backend=0,
                credentials={
                    'key': self.user.primary_email,
                    'secret': 'invalid',
                },
            )

    def test_authenticate_user_decode_token(self):
        self._mock_get_organization()
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
        self._mock_get_organization()
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
            client_type=token_pb2.IOS,
            organization_domain=self.organization.domain,
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
        self._mock_get_organization()
        response = self.client.call_action(
            'authenticate_user',
            backend=authenticate_user_pb2.RequestV1.GOOGLE,
            credentials={
                'key': 'some-code',
                'secret': 'some-id-token',
            },
            client_type=token_pb2.ANDROID,
            organization_domain=self.organization.domain,
        )
        self.assertEqual(response.result.user.primary_email, 'mwhahn@gmail.com')
        self.assertTrue(response.result.new_user)

    @patch.object(google_provider.OAuth2Credentials, '_refresh')
    @patch('users.providers.google.verify_id_token')
    @patch.object(providers.Google, '_get_profile')
    @patch('users.providers.google.credentials_from_code')
    def test_authenticate_user_google_new_user_web(
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
        self._mock_get_organization()
        response = self.client.call_action(
            'authenticate_user',
            backend=authenticate_user_pb2.RequestV1.GOOGLE,
            credentials={
                'key': 'some-code',
            },
            client_type=token_pb2.WEB,
            organization_domain=self.organization.domain,
        )
        self.assertEqual(response.result.user.primary_email, 'mwhahn@gmail.com')
        self.assertTrue(response.result.new_user)
        self.assertEqual(mocked_credentials_from_code.call_args[1]['redirect_uri'], 'postmessage')

    def test_authenticate_user_okta(self):
        identity = factories.IdentityFactory.create(provider=user_containers.IdentityV1.OKTA)
        user = identity.user.to_protobuf()
        auth_state = okta_provider.get_state_for_user(user, 'example')
        self._mock_get_organization()
        response = self.client.call_action(
            'authenticate_user',
            backend=authenticate_user_pb2.RequestV1.OKTA,
            credentials={
                'secret': auth_state,
            },
            client_type=token_pb2.WEB,
            organization_domain=self.organization.domain,
        )
        self.verify_containers(response.result.user, user)

    # def test_complete_authorization_auth_state(self):
        # user = factories.UserFactory.create()
        # factories.IdentityFactory.create(
            # user=user,
            # provider=user_containers.IdentityV1.OKTA,
        # )
        # user = user.to_protobuf()
        # auth_state = get_state_for_user(user, 'lunohq')
        # response = self.client.call_action(
            # 'complete_authorization',
            # provider=user_containers.IdentityV1.OKTA,
            # saml_details={
                # 'auth_state': auth_state,
            # },
        # )
        # self.verify_containers(user, response.result.user)

        # # verify that the auth_state can no longer be used
        # with self.assertRaisesCallActionError() as e:
            # self.client.call_action(
                # 'complete_authorization',
                # provider=user_containers.IdentityV1.OKTA,
                # saml_details={
                    # 'auth_state': auth_state,
                # },
            # )
        # self.assertIn('INVALID_AUTH_STATE', e.exception.response.errors)
