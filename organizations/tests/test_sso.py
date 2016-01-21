import service.control
from services.test import (
    mocks,
    MockedTestCase,
)

from .. import factories


class OrganizationSSOTests(MockedTestCase):

    def setUp(self):
        super(OrganizationSSOTests, self).setUp()
        self.organization = factories.OrganizationFactory.create()
        token = mocks.mock_token(organization_id=self.organization.id)
        self.client = service.control.Client('organization', token=token)
        self.mock.instance.dont_mock_service('organization')

    def test_get_sso_metadata_domain_does_not_exist(self):
        client = service.control.Client('organization', token=mocks.mock_token())
        with self.assertFieldError('organization_id', 'DOES_NOT_EXIST'):
            client.call_action('get_sso_metadata')

    def test_get_sso_metadata(self):
        sso = factories.SSOFactory.create_protobuf(organization=self.organization)
        response = self.client.call_action('get_sso_metadata')
        self.verify_containers(sso, response.result.sso)
