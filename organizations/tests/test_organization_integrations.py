import service.control
from protobufs.services.organization.containers import integration_pb2
from services.test import (
    fuzzy,
    mocks,
    TestCase,
)
from services.token import make_admin_token

from .. import (
    factories,
    models,
)


class OrganizationIntegrationTests(TestCase):

    def setUp(self):
        super(OrganizationIntegrationTests, self).setUp()
        self.organization = factories.OrganizationFactory.create()
        self.profile = mocks.mock_profile(organization_id=str(self.organization.id))
        self.token = mocks.mock_token(
            organization_id=self.organization.id,
            profile_id=self.profile.id,
        )
        self.client = service.control.Client('organization', token=self.token)

    def test_organization_enable_integration_slack_slash_command(self):
        slack_token = fuzzy.FuzzyText().fuzz()
        team_id = fuzzy.FuzzyText().fuzz()
        response = self.client.call_action(
            'enable_integration',
            integration={
                'integration_type': integration_pb2.SLACK_SLASH_COMMAND,
                'slack_slash_command': {
                    'token': slack_token,
                },
                'provider_uid': team_id,
            },
        )
        self.assertEqual(
            response.result.integration.integration_type,
            integration_pb2.SLACK_SLASH_COMMAND,
        )
        details = response.result.integration.slack_slash_command
        self.assertEqual(details.token, slack_token)

        integration = models.Integration.objects.get(pk=response.result.integration.id)
        self.assertEqual(integration.provider_uid, team_id)
        self.assertEqual(integration.type, integration_pb2.SLACK_SLASH_COMMAND)
        self.assertEqual(integration.details, response.result.integration.slack_slash_command)

    def test_organization_enable_slack_web_api(self):
        slack_token = fuzzy.FuzzyUUID().fuzz()
        scopes = ['channels:history', 'groups:history']
        response = self.client.call_action(
            'enable_integration',
            integration={
                'integration_type': integration_pb2.SLACK_WEB_API,
                'slack_web_api': {
                    'token': slack_token,
                    'scopes': scopes,
                    'team_id': 'lunohq',
                },
            },
        )

        integration = response.result.integration
        self.assertEqual(integration.integration_type, integration_pb2.SLACK_WEB_API)
        self.assertEqual(integration.slack_web_api.token, slack_token)
        self.assertEqual(integration.slack_web_api.scopes, scopes)
        self.assertEqual(integration.slack_web_api.team_id, 'lunohq')

        integration = models.Integration.objects.get(pk=integration.id)
        self.assertEqual(integration.type, integration_pb2.SLACK_WEB_API)
        self.assertEqual(response.result.integration.slack_web_api, integration.details)
        self.assertTrue(models.Integration.objects.filter(provider_uid=None).exists())

    def test_organization_get_integration_provider_uid(self):
        integration = factories.IntegrationFactory.create_protobuf(
            organization=self.organization,
            type=integration_pb2.SLACK_SLASH_COMMAND,
        )

        response = self.client.call_action(
            'get_integration',
            integration_type=integration_pb2.SLACK_SLASH_COMMAND,
            provider_uid=integration.provider_uid,
        )
        self.verify_containers(integration, response.result.integration)

    def test_organization_get_integration_provider_uid_no_organization_token(self):
        client = service.control.Client('organization', token=make_admin_token())
        integration = factories.IntegrationFactory.create_protobuf(
            organization=self.organization,
            type=integration_pb2.SLACK_SLASH_COMMAND,
        )

        response = client.call_action(
            'get_integration',
            integration_type=integration_pb2.SLACK_SLASH_COMMAND,
            provider_uid=integration.provider_uid,
        )
        self.verify_containers(integration, response.result.integration)

    def test_organization_enable_integration_duplicates(self):
        integration = integration_pb2.IntegrationV1(
            integration_type=integration_pb2.SLACK_SLASH_COMMAND,
            slack_slash_command={'token': fuzzy.text()},
        )
        response = self.client.call_action('enable_integration', integration=integration)
        self.assertTrue(response.result.integration.id)

        with self.assertFieldError('integration.integration_type', 'DUPLICATE'):
            self.client.call_action('enable_integration', integration=integration)

    def test_organization_disable_integration_does_not_exist(self):
        with self.assertFieldError('integration_type', 'DOES_NOT_EXIST'):
            self.client.call_action(
                'disable_integration',
                integration_type=integration_pb2.SLACK_SLASH_COMMAND,
            )

    def test_organization_disable_integration(self):
        factories.IntegrationFactory.create_protobuf(
            organization=self.organization,
            type=integration_pb2.SLACK_SLASH_COMMAND,
        )
        queryset = models.Integration.objects.filter(
            organization=self.organization,
            type=integration_pb2.SLACK_SLASH_COMMAND,
        )
        self.assertTrue(queryset.exists())
        self.client.call_action(
            'disable_integration',
            integration_type=integration_pb2.SLACK_SLASH_COMMAND,
        )
        self.assertFalse(queryset.exists())

    def test_organization_get_integration(self):
        expected = factories.IntegrationFactory.create_protobuf(organization=self.organization)
        response = self.client.call_action(
            'get_integration',
            integration_type=integration_pb2.SLACK_SLASH_COMMAND,
        )
        self.verify_containers(expected, response.result.integration)

    def test_organization_get_integration_does_not_exist(self):
        with self.assertFieldError('integration_type', 'DOES_NOT_EXIST'):
            self.client.call_action(
                'get_integration',
                integration_type=integration_pb2.SLACK_SLASH_COMMAND,
            )
