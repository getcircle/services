import service.control
from protobufs.services.organization.containers import integration_pb2
from services.test import (
    mocks,
    TestCase,
)

from .. import (
    factories,
    models,
)


class OrganizationIntegrationTests(TestCase):

    def setUp(self):
        super(OrganizationIntegrationTests, self).setUp()
        self.organization = factories.OrganizationFactory.create()
        self.token = mocks.mock_token(organization_id=self.organization.id)
        self.client = service.control.Client('organization', token=self.token)

    def test_organization_enable_integration_integartion_required(self):
        with self.assertFieldError('integration', 'MISSING'):
            self.client.call_action('enable_integration')

    def test_organization_enable_integration_integration_type_required(self):
        with self.assertFieldError('integration.integration_type', 'MISSING'):
            self.client.call_action(
                'enable_integration',
                integration={'google_groups': {'admin_email': 'michael@circlehq.co'}},
            )

    def test_organization_enable_integration(self):
        response = self.client.call_action(
            'enable_integration',
            integration={
                'integration_type': integration_pb2.GOOGLE_GROUPS,
                'google_groups': {
                    'admin_email': 'michael@circlehq.co',
                    'scopes': ['scope1', 'scope2'],
                }
            },
        )
        self.assertEqual(
            response.result.integration.integration_type,
            integration_pb2.GOOGLE_GROUPS,
        )
        details = response.result.integration.google_groups
        self.assertEqual(details.admin_email, 'michael@circlehq.co')
        self.assertEqual(details.scopes, ['scope1', 'scope2'])

        integration = models.Integration.objects.get(pk=response.result.integration.id)
        self.assertEqual(integration.details, response.result.integration.google_groups)
        self.assertEqual(integration.type, integration_pb2.GOOGLE_GROUPS)

    def test_organization_enable_integration_default_scopes(self):
        response = self.client.call_action(
            'enable_integration',
            integration={'integration_type': integration_pb2.GOOGLE_GROUPS},
        )
        self.assertEqual(len(response.result.integration.google_groups.scopes), 3)

    def test_organization_enable_integration_duplicates(self):
        integration = integration_pb2.IntegrationV1(integration_type=integration_pb2.GOOGLE_GROUPS)
        response = self.client.call_action('enable_integration', integration=integration)
        self.assertTrue(response.result.integration.id)

        with self.assertFieldError('integration.integration_type', 'DUPLICATE'):
            self.client.call_action('enable_integration', integration=integration)

    def test_organization_disable_integration_integration_type_required(self):
        with self.assertFieldError('integration_type', 'MISSING'):
            self.client.call_action('disable_integration')

    def test_organization_disable_integration_does_not_exist(self):
        with self.assertFieldError('integration_type', 'DOES_NOT_EXIST'):
            self.client.call_action(
                'disable_integration',
                integration_type=integration_pb2.GOOGLE_GROUPS,
            )

    def test_organization_disable_integration(self):
        factories.IntegrationFactory.create_protobuf(
            organization=self.organization,
        )
        queryset = models.Integration.objects.filter(
            organization=self.organization,
            type=integration_pb2.GOOGLE_GROUPS,
        )
        self.assertTrue(queryset.exists())
        self.client.call_action(
            'disable_integration',
            integration_type=integration_pb2.GOOGLE_GROUPS,
        )
        self.assertFalse(queryset.exists())

    def test_organization_get_integration_integration_type_required(self):
        with self.assertFieldError('integration_type', 'MISSING'):
            self.client.call_action('get_integration')

    def test_organization_get_integration(self):
        expected = factories.IntegrationFactory.create_protobuf(organization=self.organization)
        response = self.client.call_action(
            'get_integration',
            integration_type=integration_pb2.GOOGLE_GROUPS,
        )
        self.verify_containers(expected, response.result.integration)

    def test_organization_get_integration_does_not_exist(self):
        with self.assertFieldError('integration_type', 'DOES_NOT_EXIST'):
            self.client.call_action(
                'get_integration',
                integration_type=integration_pb2.GOOGLE_GROUPS,
            )
