from protobufs.user_service_pb2 import UserService
import service.control

from services.test import (
    fuzzy,
    TestCase,
)

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
        factories.IdentityFactory.create(user=user, provider=UserService.LINKEDIN)
        factories.IdentityFactory.create(user=user, provider=UserService.GOOGLE)
        response = self.client.call_action('get_identities', user_id=str(user.id))
        self.assertEqual(len(response.result.identities), 2)

    def test_delete_identity_invalid_user_id(self):
        with self.assertFieldError('user_id'):
            self.client.call_action(
                'delete_identity',
                id=fuzzy.FuzzyUUID().fuzz(),
                user_id='invalid',
            )

    def test_delete_identity_invalid_id(self):
        with self.assertFieldError('id'):
            self.client.call_action(
                'delete_identity',
                id='invalid',
                user_id=fuzzy.FuzzyUUID().fuzz(),
            )

    def test_delete_identity_id_required(self):
        with self.assertFieldError('id', 'MISSING'):
            self.client.call_action(
                'delete_identity',
                user_id=fuzzy.FuzzyUUID().fuzz(),
            )

    def test_delete_identity(self):
        user = factories.UserFactory.create()
        identity = factories.IdentityFactory.create(user=user, provider=UserService.LINKEDIN)
        factories.IdentityFactory.create(user=user, provider=UserService.GOOGLE)
        self.client.call_action(
            'delete_identity',
            id=str(identity.id),
            user_id=str(user.id),
        )
        self.assertEqual(models.Identity.objects.filter(user_id=user.id).count(), 1)
