import service.control
from services.test import TestCase
from services.token import parse_token

from .. import factories


class TestUsersAuthentication(TestCase):

    def setUp(self):
        super(TestUsersAuthentication, self).setUp()
        self.client = service.control.Client('user')
        self.user = factories.UserFactory.create_protobuf(password='password')

    def _authenticate_user(self):
        return self.client.call_action(
            'authenticate_user',
            backend=0,
            credentials={
                'key': self.user.primary_email,
                'secret': 'password',
            },
        )

    def test_authenticate_user(self):
        response = self._authenticate_user()
        self.assertTrue(response.success)
        self.assertTrue(response.result.token)
        self._verify_containers(response.result.user, self.user)

    def test_authenticate_user_invalid_password(self):
        with self.assertRaises(self.client.CallActionError):
            self.client.call_action(
                'authenticate_user',
                backend=0,
                credentials={
                    'key': self.user.primary_email,
                    'secret': 'invalid',
                },
            )

    def test_authenticate_user_decode_token(self):
        response = self._authenticate_user()
        self.assertTrue(response.success)
        token = parse_token(response.result.token)
        self.assertTrue(token.auth_token)
        self.assertTrue(token.user_id)
