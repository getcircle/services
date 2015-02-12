from protobufs.user_service_pb2 import UserService
import service.control

from services.test import TestCase

from .. import factories


class TestGetIdentities(TestCase):

    def setUp(self):
        super(TestGetIdentities, self).setUp()
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
