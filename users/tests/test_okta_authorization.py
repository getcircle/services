import json

from mock import (
    MagicMock,
    patch,
)
from protobufs.services.user import containers_pb2 as user_containers
import service.control
from service.transports.mock import get_mockable_response
from services.test import (
    fuzzy,
    mocks,
    MockedTestCase,
)
from services.token import make_admin_token

from .. import factories
from ..actions import get_authorization_instructions
from ..providers.okta import (
    get_signer,
    get_state_for_user,
    OktaSSONotEnabled,
)


class TestOktaAuthorization(MockedTestCase):

    def setUp(self):
        super(TestOktaAuthorization, self).setUp()
        self.client = service.control.Client('user')
        self.mock.instance.dont_mock_service('user')
        self.organization = mocks.mock_organization(domain='lunohq')
        token = make_admin_token(organization_id=self.organization.id)
        self.authenticated_client = service.control.Client('user', token=token)

    def _patch_saml_client(self, saml_client, identity_data):
        saml_client().parse_authn_request_response().get_identity.return_value = identity_data

    def _mock_user_info(self):
        return {
            'Email': ['michael@lunohq.com'],
            'FirstName': ['Michael'],
            'LastName': ['Hahn'],
        }

    def _mock_get_organization(self, organization=None):
        organization = organization or self.organization
        self.mock.instance.register_mock_object(
            service='organization',
            action='get_organization',
            return_object_path='organization',
            return_object=organization,
        )

    def _setup_test(self, saml_client, profile_exists=True, user_id=None, **overrides):
        domain = overrides.get('domain', 'lunohq')
        self.mock.instance.register_mock_object(
            service='organization',
            action='get_sso',
            return_object_path='sso',
            return_object=mocks.mock_sso(organization_id=self.organization.id),
            organization_domain=domain,
        )
        self._mock_get_organization()
        response = get_mockable_response('profile', 'profile_exists')
        if profile_exists:
            response.user_id = user_id or fuzzy.FuzzyUUID().fuzz()
            response.profile_id = fuzzy.FuzzyUUID().fuzz()
            response.exists = True

        self.mock.instance.register_mock_response(
            'profile',
            'profile_exists',
            mock_response=response,
            domain=domain,
            authentication_identifier='michael@lunohq.com',
        )
        self._patch_saml_client(saml_client, self._mock_user_info())
        return mocks.mock_saml_details(**overrides)

    def test_get_authorization_instructions_does_not_exist(self):
        self._mock_get_organization()
        self.mock.instance.register_mock_call_action_error(
            service='organization',
            action='get_sso',
            errors=['DOES_NOT_EXIST'],
            error_details={},
            organization_domain=self.organization.domain,
        )
        with self.assertRaises(OktaSSONotEnabled):
            get_authorization_instructions(
                user_containers.IdentityV1.OKTA,
                organization=self.organization,
            )

    def test_get_authorization_instructions(self):
        self._setup_test(MagicMock())
        self._mock_get_organization()
        authorization_url, provider_name = get_authorization_instructions(
            user_containers.IdentityV1.OKTA,
            organization=self.organization,
        )
        self.assertTrue(authorization_url)
        self.assertEqual(provider_name, 'Okta')

    def test_get_authorization_instructions_redirect_uri(self):
        redirect_uri = 'testredirecturi'
        self._setup_test(MagicMock())
        with self.settings(USER_SERVICE_ALLOWED_REDIRECT_URIS_REGEX_WHITELIST=(redirect_uri,)):
            authorization_url, provider_name = get_authorization_instructions(
                user_containers.IdentityV1.OKTA,
                organization=self.organization,
                redirect_uri=redirect_uri,
            )
        self.assertTrue(authorization_url)
        # testing for the period at the end of the string is for verifying its signed
        self.assertIn('testredirecturi.', authorization_url)

    @patch('users.authentication.utils.get_saml_client')
    def test_complete_authorization_redirect_uri_specified(self, patched_saml_client):
        redirect_uri = 'testredirecturi'
        signer = get_signer('lunohq')
        relay_state = signer.sign(redirect_uri)
        user = factories.UserFactory.create_protobuf(
            primary_email='michael@lunohq.com',
            organization_id=self.organization.id,
        )
        saml_details = self._setup_test(
            patched_saml_client,
            relay_state=relay_state,
            user_id=user.id,
        )
        with self.settings(USER_SERVICE_ALLOWED_REDIRECT_URIS_REGEX_WHITELIST=(redirect_uri,)):
            response = self.client.call_action(
                'complete_authorization',
                provider=user_containers.IdentityV1.OKTA,
                saml_details=saml_details,
            )
        self.assertEqual(response.result.redirect_uri, redirect_uri)

    @patch('users.authentication.utils.get_saml_client')
    def test_complete_authorization_invalid_relay_state(self, patched_saml_client):
        relay_state = 'testredirecturi'
        saml_details = self._setup_test(patched_saml_client, relay_state=relay_state)
        with self.assertRaisesCallActionError():
            self.client.call_action(
                'complete_authorization',
                provider=user_containers.IdentityV1.OKTA,
                saml_details=saml_details,
            )

    @patch('users.authentication.utils.get_saml_client')
    def test_complete_authorization(self, patched_saml_client):
        user = factories.UserFactory.create_protobuf(
            primary_email='michael@lunohq.com',
            organization_id=self.organization.id,
        )
        saml_details = self._setup_test(patched_saml_client, user_id=user.id)
        response = self.client.call_action(
            'complete_authorization',
            provider=user_containers.IdentityV1.OKTA,
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
            organization_id=self.organization.id,
        )
        identity = factories.IdentityFactory.create_protobuf(
            email='michael@lunohq.com',
            provider=user_containers.IdentityV1.OKTA,
            provider_uid='michael@lunohq.com',
            full_name='Michael Hahn',
            data=json.dumps(self._mock_user_info()),
            user=user,
            organization_id=self.organization.id,
        )
        # above facotry requires user model, below we test with the protobuf
        user = user.to_protobuf()
        saml_details = self._setup_test(patched_saml_client, user_id=user.id)
        response = self.client.call_action(
            'complete_authorization',
            provider=user_containers.IdentityV1.OKTA,
            saml_details=saml_details,
        )
        self.verify_containers(response.result.identity, identity)
        self.verify_containers(response.result.user, user)

    @patch('users.authentication.utils.get_saml_client')
    def test_complete_authorization_invalid_organization(self, patched_saml_client):
        factories.UserFactory.create_protobuf(
            primary_email='michael@lunohq.com',
        )
        saml_details = self._setup_test(
            patched_saml_client,
            domain='example',
            profile_exists=False,
        )
        with self.assertRaisesCallActionError() as expected:
            self.client.call_action(
                'complete_authorization',
                provider=user_containers.IdentityV1.OKTA,
                saml_details=saml_details,
            )
        self.assertIn('PROFILE_NOT_FOUND', expected.exception.response.errors)
