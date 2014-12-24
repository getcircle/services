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
        action_response, _ = self.client.call_action(
            'create_user',
            password='s',
            identity=self.identity_data,
        )
        self.assertFalse(action_response.result.success)
        self.assertIn('FIELD_ERROR', action_response.result.errors)
        error = action_response.result.error_details[0]
        self.assertEqual(error.detail, 'INVALID_MIN_LENGTH')

    def test_create_user_maximum_password_length(self):
        action_response, _ = self.client.call_action(
            'create_user',
            password='s' * 100,
            identity=self.identity_data,
        )
        self.assertFalse(action_response.result.success)
        self.assertIn('FIELD_ERROR', action_response.result.errors)
        error = action_response.result.error_details[0]
        self.assertEqual(error.detail, 'INVALID_MAX_LENGTH')

    def test_create_user(self):
        # XXX we should be stubbing out the call to the identity_service within
        # this action
        action_response, response = self.client.call_action(
            'create_user',
            password='a_valid_password',
            identity=self.identity_data,
        )
        self.assertTrue(action_response.result.success)

        self.assertTrue(uuid.UUID(response.user.id, version=4))
        self.assertEqual(
            response.user.primary_email,
            self.identity_data['email'],
        )
        self.assertTrue(response.user.is_active)
        self.assertFalse(response.user.is_admin)

        identity = response.identities[0]
        self.assertEqual(identity.first_name, self.identity_data['first_name'])
        self.assertEqual(identity.last_name, self.identity_data['last_name'])
        self.assertEqual(identity.email, self.identity_data['email'])
