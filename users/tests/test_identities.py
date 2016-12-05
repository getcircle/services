from protobufs.services.user import containers_pb2 as user_containers
import mock
import service.control

from services.test import TestCase

from .. import (
    factories,
    models,
)


class TestIdentities(TestCase):

    def setUp(self):
        super(TestIdentities, self).setUp()
        self.client = service.control.Client('user', token='test-token')

    def test_get_identities_invalid_user_id(self):
        with self.assertFieldError('user_id', 'INVALID'):
            self.client.call_action('get_identities', user_id='invalid')

    def test_get_identities(self):
        user = factories.UserFactory.create()
        factories.IdentityFactory.create(user=user, provider=user_containers.IdentityV1.GOOGLE)
        response = self.client.call_action('get_identities', user_id=str(user.id))
        self.assertEqual(len(response.result.identities), 1)

    def test_delete_identity_invalid_user_id(self):
        with self.assertFieldError('identity.user_id'):
            container = factories.IdentityFactory.build_protobuf()
            container.user_id = 'invalid'
            self.client.call_action('delete_identity', identity=container)

    def test_delete_identity_invalid_id(self):
        with self.assertFieldError('identity.id'):
            self.client.call_action(
                'delete_identity',
                identity=factories.IdentityFactory.build_protobuf(id='invalid'),
            )

    def test_delete_identity_id_required(self):
        with self.assertFieldError('identity.id', 'MISSING'):
            self.client.call_action(
                'delete_identity',
                identity=factories.IdentityFactory.build_protobuf(id=None),
            )

    def test_delete_identity_user_id_required(self):
        with self.assertFieldError('identity.user_id', 'MISSING'):
            container = factories.IdentityFactory.build_protobuf()
            container.ClearField('user_id')
            self.client.call_action('delete_identity', identity=container)

    @mock.patch('users.actions.providers.Google')
    def test_delete_identity(self, mock_provider):
        user = factories.UserFactory.create()
        identity = factories.IdentityFactory.create_protobuf(
            user=user,
            provider=user_containers.IdentityV1.GOOGLE,
        )
        self.client.call_action('delete_identity', identity=identity)
        self.assertEqual(models.Identity.objects.filter(user_id=user.id).count(), 0)
