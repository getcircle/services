import json

from mock import (
    MagicMock,
    patch,
)
from protobufs.services.user import containers_pb2 as user_containers
import service.control
from services.test import (
    mocks,
    MockedTestCase,
)

from .. import factories
from ..providers.saml import (
    get_signer,
    get_state_for_user,
    parse_state,
)


class TestSAMLAuthorization(MockedTestCase):

    def setUp(self):
        super(TestSAMLAuthorization, self).setUp()
        self.client = service.control.Client('user')
        self.mock.instance.dont_mock_service('user')

    def _patch_saml_client(self, saml_client, identity_data):
        saml_client().parse_authn_request_response().get_identity.return_value = identity_data

    def _mock_user_info(self):
        return {
            'Email': ['michael@lunohq.com'],
            'FirstName': ['Michael'],
            'LastName': ['Hahn'],
        }

    def _setup_test(self, saml_client, mock, **overrides):
        mock.instance.register_mock_object(
            service='organization',
            action='get_sso_metadata',
            return_object_path='sso',
            return_object=mocks.mock_sso(),
            organization_domain='lunohq',
        )
        mock.instance.register_empty_response(
            service='profile',
            action='get_profile',
            mock_regex_lookup='profile:get_profile:.*',
        )
        self._patch_saml_client(saml_client, self._mock_user_info())
        return mocks.mock_saml_details(**overrides)

    def test_get_authorization_instructions_does_not_exist(self):
        with self.assertFieldError('domain', 'DOES_NOT_EXIST'), self.mock_transport() as mock:
            mock.instance.register_mock_call_action_error(
                service_name='organization',
                action_name='get_sso_metadata',
                errors=['DOES_NOT_EXIST'],
                error_details={},
                organization_domain='example',
            )
            self.client.call_action(
                'get_authorization_instructions',
                provider=user_containers.IdentityV1.SAML,
                domain='example',
            )

    def test_get_authorization_instructions(self):
        with self.mock_transport() as mock:
            self._setup_test(MagicMock(), mock)
            response = self.client.call_action(
                'get_authorization_instructions',
                provider=user_containers.IdentityV1.SAML,
                domain='lunohq',
            )
        self.assertTrue(response.result.authorization_url)

    def test_get_authorization_instructions_redirect_uri(self):
        with self.mock_transport() as mock:
            self._setup_test(MagicMock(), mock)
            response = self.client.call_action(
                'get_authorization_instructions',
                provider=user_containers.IdentityV1.SAML,
                domain='lunohq',
                redirect_uri='testredirecturi',
            )
        self.assertTrue(response.result.authorization_url)
        # testing for the period at the end of the string is for verifying its signed
        self.assertIn('testredirecturi.', response.result.authorization_url)

    @patch('users.authentication.utils.get_saml_client')
    def test_complete_authorization_redirect_uri_specified(self, patched_saml_client):
        redirect_uri = 'testredirecturi'
        signer = get_signer('lunohq')
        relay_state = signer.sign(redirect_uri)
        with self.mock_transport() as mock, self.settings(
            USER_SERVICE_ALLOWED_REDIRECT_URIS=(redirect_uri,)
        ):
            saml_details = self._setup_test(patched_saml_client, mock, relay_state=relay_state)
            response = self.client.call_action(
                'complete_authorization',
                provider=user_containers.IdentityV1.SAML,
                saml_details=saml_details,
            )
        self.assertEqual(response.result.redirect_uri, redirect_uri)

    @patch('users.authentication.utils.get_saml_client')
    def test_complete_authorization_invalid_relay_state(self, patched_saml_client):
        relay_state = 'testredirecturi'
        with self.mock_transport() as mock, self.assertRaisesCallActionError():
            saml_details = self._setup_test(patched_saml_client, mock, relay_state=relay_state)
            self.client.call_action(
                'complete_authorization',
                provider=user_containers.IdentityV1.SAML,
                saml_details=saml_details,
            )

    @patch('users.authentication.utils.get_saml_client')
    def test_complete_authorization_no_user(self, patched_saml_client):
        with self.mock_transport() as mock:
            saml_details = self._setup_test(patched_saml_client, mock)
            response = self.client.call_action(
                'complete_authorization',
                provider=user_containers.IdentityV1.SAML,
                saml_details=saml_details,
            )
        self.assertEqual(response.result.identity.provider, user_containers.IdentityV1.SAML)
        self.assertEqual(response.result.identity.email, 'michael@lunohq.com')
        self.assertEqual(response.result.identity.provider_uid, 'michael@lunohq.com')
        parsed_state = parse_state(response.result.saml_details.auth_state)
        self.assertEqual(parsed_state['user_id'], response.result.user.id)
        self.assertTrue(parsed_state['totp'])

    @patch('users.authentication.utils.get_saml_client')
    def test_complete_authorization(self, patched_saml_client):
        user = factories.UserFactory.create_protobuf(
            primary_email='michael@lunohq.com',
        )
        with self.mock_transport() as mock:
            saml_details = self._setup_test(patched_saml_client, mock)
            response = self.client.call_action(
                'complete_authorization',
                provider=user_containers.IdentityV1.SAML,
                saml_details=saml_details,
            )
        self.assertEqual(response.result.identity.email, 'michael@lunohq.com')
        self.assertEqual(response.result.identity.provider_uid, 'michael@lunohq.com')
        self.assertEqual(response.result.identity.full_name, 'Michael Hahn')
        self.verify_containers(response.result.user, user)

    @patch('users.authentication.utils.get_saml_client')
    def test_complete_authorization_identity_exists(self, patched_saml_client):
        user = factories.UserFactory.create(
            primary_email='michael@lunohq.com',
        )
        identity = factories.IdentityFactory.create_protobuf(
            email='michael@lunohq.com',
            provider=user_containers.IdentityV1.SAML,
            provider_uid='michael@lunohq.com',
            full_name='Michael Hahn',
            data=json.dumps(self._mock_user_info()),
            user=user,
        )
        # above facotry requires user model, below we test with the protobuf
        user = user.to_protobuf()
        with self.mock_transport() as mock:
            saml_details = self._setup_test(patched_saml_client, mock)
            response = self.client.call_action(
                'complete_authorization',
                provider=user_containers.IdentityV1.SAML,
                saml_details=saml_details,
            )
        self.verify_containers(response.result.identity, identity)
        self.verify_containers(response.result.user, user)

    def test_complete_authorization_auth_state(self):
        user = factories.UserFactory.create()
        factories.IdentityFactory.create(
            user=user,
            provider=user_containers.IdentityV1.SAML,
        )
        user = user.to_protobuf()
        auth_state = get_state_for_user(user)
        response = self.client.call_action(
            'complete_authorization',
            provider=user_containers.IdentityV1.SAML,
            saml_details={
                'auth_state': auth_state,
            },
        )
        self.verify_containers(user, response.result.user)

        # verify that the auth_state can no longer be used
        with self.assertRaisesCallActionError() as e:
            self.client.call_action(
                'complete_authorization',
                provider=user_containers.IdentityV1.SAML,
                saml_details={
                    'auth_state': auth_state,
                },
            )
        self.assertIn('INVALID_AUTH_STATE', e.exception.response.errors)