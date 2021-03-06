import service.control
from services.test import MockedTestCase

from .. import factories


class OrganizationSSOTests(MockedTestCase):

    def setUp(self):
        super(OrganizationSSOTests, self).setUp()
        self.organization = factories.OrganizationFactory.create()
        self.client = service.control.Client('organization')
        self.mock.instance.dont_mock_service('organization')

    def test_get_sso_domain_does_not_exist(self):
        with self.assertFieldError('organization_domain', 'DOES_NOT_EXIST'):
            self.client.call_action('get_sso', organization_domain='doesnotexist')

    def test_get_sso_domain_required(self):
        with self.assertFieldError('organization_domain', 'MISSING'):
            self.client.call_action('get_sso')

    def test_get_sso(self):
        sso = factories.SSOFactory.create_protobuf(organization=self.organization)
        response = self.client.call_action('get_sso', organization_domain=self.organization.domain)
        self.verify_containers(sso, response.result.sso)
