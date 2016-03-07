import urlparse

import service.control
from protobufs.services.organization.containers import sso_pb2
from protobufs.services.user.actions import authenticate_user_pb2
from protobufs.services.user import containers_pb2 as user_containers
from services.test import (
    mocks,
    MockedTestCase,
)

from .. import factories
from ..providers.base import parse_state_token


class Test(MockedTestCase):

    def setUp(self):
        super(Test, self).setUp()
        self.organization = mocks.mock_organization()
        self.client = service.control.Client('user')
        self.mock.instance.dont_mock_service('user')

    def _mock_get_organization(self, organization=None):
        organization = organization or self.organization
        self.mock.instance.register_mock_object(
            service='organization',
            action='get_organization',
            return_object_path='organization',
            return_object=organization,
            domain=organization.domain,
        )

    def test_get_authentication_instructions_organization_domain_required(self):
        with self.assertFieldError('organization_domain', 'MISSING'):
            self.client.call_action('get_authentication_instructions')

    def test_get_authentication_instructions_email_invalid(self):
        with self.assertFieldError('email'):
            self.client.call_action(
                'get_authentication_instructions',
                email='invalid@invalid',
                organization_domain=self.organization.domain,
            )

    def test_get_authentication_instructions_organization_domain_does_not_exist(self):
        error = self.mock.get_mockable_call_action_error(
            service='organization',
            action='get_organization',
            errors=['FIELD_ERROR'],
            error_details=[{'key': 'domain', 'detail': 'DOES_NOT_EXIST', 'error': 'FIELD_ERROR'}],
        )
        self.mock.instance.register_mock_error(
            service='organization',
            action='get_organization',
            error=error,
            domain='doesnotexist',
        )
        with self.assertFieldError('organization_domain', 'DOES_NOT_EXIST'):
            self.client.call_action(
                'get_authentication_instructions',
                organization_domain='doesnotexist',
            )

    def test_get_authentication_instructions_organization_domain_no_sso(self):
        response = self.client.call_action(
            'get_authentication_instructions',
            organization_domain=self.organization.domain,
        )
        # should default to internal backend since we don't have any sso setup
        self.assertEqual(response.result.backend, authenticate_user_pb2.RequestV1.INTERNAL)

    def test_get_authentication_instructions_organization_sso_okta(self):
        self.mock.instance.register_mock_object(
            service='organization',
            action='get_sso',
            return_object_path='sso',
            return_object=mocks.mock_sso(),
            organization_domain=self.organization.domain,
        )
        self._mock_get_organization()
        response = self.client.call_action(
            'get_authentication_instructions',
            organization_domain=self.organization.domain,
        )

        self.assertTrue(response.result.authorization_url)
        self.assertEqual(response.result.backend, authenticate_user_pb2.RequestV1.OKTA)
        self.assertTrue(response.result.provider_name, 'Okta')

    def test_get_authentication_instructions_organization_domain(self):
        self._mock_get_organization()
        response = self.client.call_action(
            'get_authentication_instructions',
            organization_domain=self.organization.domain,
        )

        self.assertEqual(response.result.organization_image_url, self.organization.image_url)

    def test_get_authentication_instructions_organization_sso_force_internal(self):
        email = 'example@example.com'
        self.mock.instance.register_mock_object(
            service='organization',
            action='get_sso',
            return_object_path='sso',
            return_object=mocks.mock_sso(),
            organization_domain=self.organization.domain,
        )
        self._mock_get_organization()
        with self.settings(USER_SERVICE_FORCE_DOMAIN_INTERNAL_AUTH=(self.organization.domain,)):
            response = self.client.call_action(
                'get_authentication_instructions',
                email=email,
                organization_domain=self.organization.domain,
            )

        self.assertFalse(response.result.authorization_url)
        self.assertEqual(response.result.backend, authenticate_user_pb2.RequestV1.INTERNAL)

    def test_get_authentication_instructions_new_user_organization_sso_google(self):
        self._mock_get_organization()
        self.mock.instance.register_mock_object(
            service='organization',
            action='get_sso',
            return_object_path='sso',
            return_object=mocks.mock_sso(
                saml=None,
                google=sso_pb2.GoogleDetailsV1(domains=['example.com']),
                provider=sso_pb2.GOOGLE,
            ),
            organization_domain=self.organization.domain,
        )
        response = self.client.call_action(
            'get_authentication_instructions',
            email='example@example.com',
            organization_domain=self.organization.domain,
        )

        self.assertTrue(response.result.authorization_url)
        self.assertEqual(response.result.backend, authenticate_user_pb2.RequestV1.GOOGLE)

    def test_get_authentication_instructions_redirect_uri_google_sso(self):
        self._mock_get_organization()
        self.mock.instance.register_mock_object(
            service='organization',
            action='get_sso',
            return_object_path='sso',
            return_object=mocks.mock_sso(
                saml=None,
                google=sso_pb2.GoogleDetailsV1(domains=['example.com']),
                provider=sso_pb2.GOOGLE,
            ),
            organization_domain=self.organization.domain,
        )
        response = self.client.call_action(
            'get_authentication_instructions',
            email='example@example.com',
            redirect_uri='https://frontend.lunohq.com/auth',
            organization_domain=self.organization.domain,
        )

        parsed_url = urlparse.urlparse(response.result.authorization_url)
        query = dict(urlparse.parse_qsl(parsed_url.query))
        parsed_state = parse_state_token(user_containers.IdentityV1.GOOGLE, query['state'])
        self.assertIn('frontend.lunohq', parsed_state['redirect_uri'])
        self.assertEqual(parsed_state['domain'], self.organization.domain)
        self.assertTrue(response.result.authorization_url)
        self.assertEqual(response.result.backend, authenticate_user_pb2.RequestV1.GOOGLE)

    def test_get_authentication_instructions_redirect_uri_invalid_google_sso(self):
        self.mock.instance.register_mock_object(
            service='organization',
            action='get_sso',
            return_object_path='sso',
            return_object=mocks.mock_sso(
                saml=None,
                google=sso_pb2.GoogleDetailsV1(domains=['example.com']),
                provider=sso_pb2.GOOGLE,
            ),
            organization_domain=self.organization.domain,
        )
        with self.assertFieldError('redirect_uri'):
            self.client.call_action(
                'get_authentication_instructions',
                email='example@example.com',
                redirect_uri='https://frontendlunohq.com/auth/success/',
                organization_domain=self.organization.domain,
            )

    def test_get_authentication_instructions_existing_user_google_sso(self):
        self._mock_get_organization()
        self.mock.instance.register_mock_object(
            service='organization',
            action='get_sso',
            return_object_path='sso',
            return_object=mocks.mock_sso(
                saml=None,
                google=sso_pb2.GoogleDetailsV1(domains=['example.com']),
                provider=sso_pb2.GOOGLE,
            ),
            organization_domain=self.organization.domain,
        )
        user = factories.UserFactory.create(
            primary_email='example@example.com',
            organization_id=self.organization.id,
        )
        response = self.client.call_action(
            'get_authentication_instructions',
            email=user.primary_email,
            organization_domain=self.organization.domain,
        )
        self.assertTrue(response.result.authorization_url)
        self.assertEqual(response.result.backend, authenticate_user_pb2.RequestV1.GOOGLE)

    def test_get_authentication_instructions_new_user(self):
        self._mock_get_organization()
        email = 'example@example.com'
        with self.settings(USER_SERVICE_FORCE_GOOGLE_AUTH=(email,)):
            response = self.client.call_action(
                'get_authentication_instructions',
                email=email,
                organization_domain=self.organization.domain,
            )
        self.assertFalse(response.result.authorization_url)
        self.assertEqual(response.result.backend, authenticate_user_pb2.RequestV1.INTERNAL)

    def test_get_authentication_instructions_existing_user(self):
        self._mock_get_organization()
        user = factories.UserFactory.create(
            primary_email='example@example.com',
            organization_id=self.organization.id,
        )
        response = self.client.call_action(
            'get_authentication_instructions',
            email=user.primary_email,
            organization_domain=self.organization.domain,
        )
        self.assertFalse(response.result.authorization_url)
        self.assertEqual(response.result.backend, authenticate_user_pb2.RequestV1.INTERNAL)

    def test_get_authentication_instructions_organization_sso_google_force_to_password(self):
        self._mock_get_organization()
        user = factories.UserFactory.create(
            primary_email='demo@circlehq.co',
            organization_id=self.organization.id,
        )
        with self.settings(USER_SERVICE_FORCE_INTERNAL_AUTH=(user.primary_email,)):
            response = self.client.call_action(
                'get_authentication_instructions',
                email=user.primary_email,
                organization_domain=self.organization.domain,
            )

        self.assertFalse(response.result.authorization_url)
        self.assertEqual(response.result.backend, authenticate_user_pb2.RequestV1.INTERNAL)

    def test_get_authentication_instructions_invalid(self):
        with self.assertFieldError('next_path'):
            self.client.call_action(
                'get_authentication_instructions',
                organization_domain=self.organization.domain,
                next_path='invalid',
            )

        with self.assertFieldError('next_path'):
            self.client.call_action(
                'get_authentication_instructions',
                organization_domain=self.organization.domain,
                next_path='https://www.google.com',
            )

        with self.assertFieldError('next_path'):
            self.client.call_action(
                'get_authentication_instructions',
                organization_domain=self.organization.domain,
                next_path='www.google.com',
            )

    def test_get_authentication_instructions_existing_user_google_sso_next_path(self):
        self._mock_get_organization()
        self.mock.instance.register_mock_object(
            service='organization',
            action='get_sso',
            return_object_path='sso',
            return_object=mocks.mock_sso(
                saml=None,
                google=sso_pb2.GoogleDetailsV1(domains=['example.com']),
                provider=sso_pb2.GOOGLE,
            ),
            organization_domain=self.organization.domain,
        )
        user = factories.UserFactory.create(
            primary_email='example@example.com',
            organization_id=self.organization.id,
        )
        response = self.client.call_action(
            'get_authentication_instructions',
            email=user.primary_email,
            organization_domain=self.organization.domain,
            next_path='/profile/1234',
        )
        self.assertTrue(response.result.authorization_url)
        self.assertEqual(response.result.backend, authenticate_user_pb2.RequestV1.GOOGLE)
        parsed_url = urlparse.urlparse(response.result.authorization_url)
        query = dict(urlparse.parse_qsl(parsed_url.query))
        parsed_state = parse_state_token(user_containers.IdentityV1.GOOGLE, query['state'])
        self.assertEqual('/profile/1234', parsed_state['next_path'])
        self.assertEqual(parsed_state['domain'], self.organization.domain)
