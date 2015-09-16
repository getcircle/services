import service.control
from services.test import MockedTestCase
from protobufs.services.user.actions.authenticate_user_pb2 import RequestV1 as AuthenticateRequest

from .. import factories


class OrganizationGetAuthenticationInstructionsTests(MockedTestCase):

    def setUp(self):
        super(OrganizationGetAuthenticationInstructionsTests, self).setUp()
        self.organization = factories.OrganizationFactory.create()
        self.client = service.control.Client('organization')
        self.mock.instance.dont_mock_service('organization')

    def test_get_authentication_instructions_domain_does_not_exist(self):
        with self.assertFieldError('domain', 'DOES_NOT_EXIST'):
            self.client.call_action('get_authentication_instructions', domain='doesnotexist')

    def test_get_authentication_instructions_domain_required(self):
        with self.assertFieldError('domain', 'MISSING'):
            self.client.call_action('get_authentication_instructions')

    def test_get_authentication_instructions_none_specified(self):
        response = self.client.call_action(
            'get_authentication_instructions',
            domain=self.organization.domain,
        )
        self.assertFalse(response.result.ListFields())

    def test_get_authentication_instructions_sso(self):
        factories.SSOFactory.create(organization=self.organization)
        response = self.client.call_action(
            'get_authentication_instructions',
            domain=self.organization.domain,
        )
        self.assertTrue(response.result.authorization_url)
        self.assertEqual(response.result.backend, AuthenticateRequest.SAML)
