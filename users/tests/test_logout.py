from rest_framework.authtoken.models import Token
import service.control

from services.test import (
    mocks,
    TestCase,
)

from .. import factories


class TestUserDevices(TestCase):

    def setUp(self):
        self.user = factories.UserFactory.create()
        self.service_token = mocks.mock_token(user_id=self.user.id)
        self.client = service.control.Client('user', token=self.service_token)

    def test_logout(self):
        Token.objects.create(user=self.user)
        self.client.call_action('logout')
        with self.assertRaises(Token.DoesNotExist):
            Token.objects.get(user=self.user)

    def test_logout_token_doesnt_exit(self):
        self.client.call_action('logout')
        with self.assertRaises(Token.DoesNotExist):
            Token.objects.get(user=self.user)

    def test_logout_only_effects_user_token(self):
        Token.objects.create(user=self.user)
        users = factories.UserFactory.create_batch(size=4)
        for user in users:
            Token.objects.create(user=user)

        self.assertEqual(len(Token.objects.all()), len(users) + 1)

        self.client.call_action('logout')
        self.assertEqual(len(Token.objects.all()), len(users))
