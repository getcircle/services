import uuid

from django.test import TestCase
import service.control

# XXX should support creating users without a password (we'll need this for the
# excel sheet or bulk upload)


class TestUserActions(TestCase):

    def setUp(self):
        self.client = service.control.Client('user', token='test-token')
        self.identity_data = {
            'first_name': 'Michael',
            'last_name': 'Hahn',
            'email': 'mwhahn@gmail.com',
        }

    def test_create_user_minimum_password_length(self):
        response = self.client.call_action(
            'create_user',
            password='s',
            identity=self.identity_data,
        )
        self.assertFalse(response.success)
        self.assertIn('FIELD_ERROR', response.errors)
        error = response.error_details[0]
        self.assertEqual(error.detail, 'INVALID_MIN_LENGTH')

    def test_create_user_maximum_password_length(self):
        response = self.client.call_action(
            'create_user',
            password='s' * 100,
            identity=self.identity_data,
        )
        self.assertFalse(response.success)
        self.assertIn('FIELD_ERROR', response.errors)
        error = response.error_details[0]
        self.assertEqual(error.detail, 'INVALID_MAX_LENGTH')

    def test_create_user(self):
        # XXX we should be stubbing out the call to the identity_service within
        # this action
        response = self.client.call_action(
            'create_user',
            password='a_valid_password',
            identity=self.identity_data,
        )
        self.assertTrue(response.success)

        self.assertTrue(uuid.UUID(response.result.user.id, version=4))
        self.assertEqual(
            response.result.user.primary_email,
            self.identity_data['email'],
        )
        self.assertTrue(response.result.user.is_active)
        self.assertFalse(response.result.user.is_admin)

        identity = response.result.identities[0]
        self.assertEqual(identity.first_name, self.identity_data['first_name'])
        self.assertEqual(identity.last_name, self.identity_data['last_name'])
        self.assertEqual(identity.email, self.identity_data['email'])
