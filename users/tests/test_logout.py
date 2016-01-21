from protobufs.services.user.containers import token_pb2
import service.control

from services.token import parse_token
from services.test import (
    mocks,
    TestCase,
)

from .. import (
    factories,
    models,
)


class Test(TestCase):

    def setUp(self):
        self.organization = mocks.mock_organization()
        self.user = factories.UserFactory.create(organization_id=self.organization.id)
        self.service_token = mocks.mock_token(
            user_id=self.user.id,
            organization_id=self.organization.id,
        )
        self.parsed_token = parse_token(self.service_token)
        self.client = service.control.Client('user', token=self.service_token)

    def test_logout_single_client_type(self):
        models.Token.objects.create(
            key=self.parsed_token.auth_token,
            user=self.user,
            client_type=token_pb2.IOS,
            organization_id=self.organization.id,
        )
        models.Token.objects.create(
            user=self.user,
            client_type=token_pb2.ANDROID,
            organization_id=self.organization.id,
        )
        self.assertEqual(models.Token.objects.filter(user=self.user).count(), 2)
        self.client.call_action('logout', client_type=token_pb2.IOS)
        self.assertEqual(models.Token.objects.filter(user=self.user).count(), 1)

    def test_logout_single_client_type_duplicate_client_types(self):
        models.Token.objects.create(
            key=self.parsed_token.auth_token,
            user=self.user,
            client_type=token_pb2.IOS,
            organization_id=self.organization.id,
        )
        models.Token.objects.create(
            user=self.user,
            client_type=token_pb2.IOS,
            organization_id=self.organization.id,
        )
        self.assertEqual(models.Token.objects.filter(user=self.user).count(), 2)
        response = self.client.call_action('logout', client_type=token_pb2.IOS)
        self.assertEqual(models.Token.objects.filter(user=self.user).count(), 1)
        self.assertEqual(response.service_response.control.token, '')

    def test_logout_token_doesnt_exit(self):
        self.client.call_action('logout', client_type=token_pb2.IOS)
        with self.assertRaises(models.Token.DoesNotExist):
            models.Token.objects.get(user=self.user)

    def test_logout_only_effects_user_token(self):
        models.Token.objects.create(
            key=self.parsed_token.auth_token,
            user=self.user,
            client_type=token_pb2.IOS,
            organization_id=self.organization.id,
        )
        users = factories.UserFactory.create_batch(size=4, organization_id=self.organization.id)
        for user in users:
            models.Token.objects.create(
                user=user,
                client_type=token_pb2.IOS,
                organization_id=self.organization.id,
            )

        self.assertEqual(len(models.Token.objects.all()), len(users) + 1)

        self.client.call_action('logout', client_type=token_pb2.IOS)
        self.assertEqual(len(models.Token.objects.all()), len(users))

    def test_logout_invalid_token_no_user_id(self):
        service_token = mocks.mock_token(user_id=None, organization_id=self.organization.id)
        client = service.control.Client('user', token=service_token)

        users = factories.UserFactory.create_batch(size=4, organization_id=self.organization.id)
        for user in users:
            models.Token.objects.create(
                user=user,
                client_type=token_pb2.IOS,
                organization_id=self.organization.id,
            )

        self.assertEqual(models.Token.objects.all().count(), len(users))
        client.call_action('logout', client_type=token_pb2.IOS)
        self.assertEqual(models.Token.objects.all().count(), len(users))

    def test_logout_revoke_all_tokens(self):
        for key, value in token_pb2.ClientTypeV1.items():
            models.Token.objects.create(
                user=self.user,
                client_type=value,
                organization_id=self.organization.id,
            )

        self.assertEqual(
            models.Token.objects.filter(user=self.user).count(),
            len(token_pb2.ClientTypeV1.values()),
        )

        self.client.call_action('logout', revoke_all=True)
        self.assertEqual(models.Token.objects.filter(user=self.user).count(), 0)
