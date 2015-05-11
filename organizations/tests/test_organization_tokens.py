import service.control
from services.token import parse_token
from services.test import (
    fuzzy,
    mocks,
    TestCase,
)

from .. import (
    factories,
    models,
)


class OrganizationTokenTests(TestCase):

    def setUp(self):
        super(OrganizationTokenTests, self).setUp()
        self.organization = factories.OrganizationFactory.create()
        self.token = mocks.mock_token(organization_id=self.organization.id)
        self.client = service.control.Client('organization', token=self.token)

    def test_create_organization_token_does_not_exist(self):
        client = service.control.Client(
            'organization',
            token=mocks.mock_token(organization_id=fuzzy.FuzzyUUID().fuzz()),
        )
        with self.assertFieldError('token.organization_id', 'DOES_NOT_EXIST'):
            client.call_action('create_token')

    def test_create_organization_token_organization_id_not_present(self):
        client = service.control.Client(
            'organization',
            token=mocks.mock_token(organization_id=None),
        )
        with self.assertFieldError('token.organization_id', 'MISSING'):
            client.call_action('create_token')

    def test_create_organization_token_invalid_organization(self):
        client = service.control.Client(
            'organization',
            token=mocks.mock_token(organization_id='invalid'),
        )
        with self.assertFieldError('token.organization_id'):
            client.call_action('create_token')

    def test_create_organization_token_user_id_not_present(self):
        client = service.control.Client(
            'organization',
            token=mocks.mock_token(organization_id=self.organization.id, user_id=None),
        )
        with self.assertFieldError('token.user_id', 'MISSING'):
            client.call_action('create_token')

    def test_create_organization_token_invalid_user_id(self):
        client = service.control.Client(
            'organization',
            token=mocks.mock_token(organization_id=self.organization.id, user_id='invalid'),
        )
        with self.assertFieldError('token.user_id'):
            client.call_action('create_token')

    def test_create_organization_token(self):
        response = self.client.call_action('create_token')
        service_token = parse_token(self.token)
        token = response.result.token
        self.assertTrue(token.key)
        self.assertEqual(token.requested_by_user_id, service_token.user_id)
        model_token = models.Token.objects.get(key=token.key)
        self.assertEqual(model_token.organization_id, self.organization.id)

    def test_get_organization_tokens(self):
        # create 2 tokens for the organization
        factories.TokenFactory.create_batch(size=2, organization=self.organization)
        # create tokens for other organizations
        factories.TokenFactory.create_batch(size=2)
        response = self.client.call_action('get_tokens')
        self.assertEqual(len(response.result.tokens), 2)
        self.assertEqual(models.Token.objects.filter(organization=self.organization).count(), 2)

    def test_get_organization_tokens_invalid_organization_id(self):
        client = service.control.Client(
            'organization',
            token=mocks.mock_token(organization_id='invalid'),
        )
        with self.assertFieldError('token.organization_id'):
            client.call_action('get_tokens')

    def test_get_organization_tokens_does_not_exist(self):
        client = service.control.Client(
            'organization',
            token=mocks.mock_token(organization_id=fuzzy.FuzzyUUID().fuzz()),
        )
        with self.assertFieldError('token.organization_id', 'DOES_NOT_EXIST'):
            client.call_action('get_tokens')
