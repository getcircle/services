import service.control
from services.test import MockedTestCase

from .. import factories


class OrganizationTeamTests(MockedTestCase):

    def setUp(self):
        super(OrganizationTeamTests, self).setUp()
        self.organization = factories.OrganizationFactory.create()
        self.client = service.control.Client('organization')
        self.mock.instance.dont_mock_service('organization')

    def test_get_sso_metadata_domain_does_not_exist(self):
        with self.assertFieldError('organization_domain', 'DOES_NOT_EXIST'):
            self.client.call_action('get_sso_metadata', organization_domain='doesnotexist')

    def test_get_sso_metadata_domain_required(self):
        with self.assertFieldError('organization_domain', 'MISSING'):
            self.client.call_action('get_sso_metadata')

    def test_get_sso_metadata(self):
        sso = factories.SSOFactory.create_protobuf(organization=self.organization)
        response = self.client.call_action(
            'get_sso_metadata',
            organization_domain=self.organization.domain,
        )
        self.verify_containers(sso, response.result.sso)
