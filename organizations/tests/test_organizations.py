import service.control

from services.test import MockedTestCase
from services.token import make_admin_token

from .. import factories


class OrganizationTests(MockedTestCase):

    def setUp(self):
        super(OrganizationTests, self).setUp()
        self.client = service.control.Client('organization', token=make_admin_token())
        self.mock.instance.dont_mock_service('organization')

    def test_create_organization(self):
        organization = factories.OrganizationFactory.build_protobuf()
        response = self.client.call_action('create_organization', organization=organization)
        self.verify_containers(organization, response.result.organization)

    def test_create_organization_duplicate_domain(self):
        organization = factories.OrganizationFactory.create_protobuf()
        organization.ClearField('id')
        with self.assertFieldError('organization.domain', 'DUPLICATE'):
            self.client.call_action('create_organization', organization=organization)

    def test_get_organization(self):
        organization = factories.OrganizationFactory.create_protobuf()
        response = self.client.call_action('get_organization', organization_id=organization.id)
        self.verify_containers(organization, response.result.organization)

    def test_get_organization_with_domain_does_not_exist(self):
        with self.assertFieldError('organization_domain', 'DOES_NOT_EXIST'):
            self.client.call_action('get_organization', organization_domain='doesnotexist.com')

    def test_get_organization_with_domain(self):
        expected = factories.OrganizationFactory.create_protobuf()
        response = self.client.call_action('get_organization', organization_domain=expected.domain)
        self.verify_containers(expected, response.result.organization)
