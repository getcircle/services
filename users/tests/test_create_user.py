import uuid

import service.control

from services.test import (
    fuzzy,
    TestCase,
)

from .. import factories


class TestUserActions(TestCase):

    def setUp(self):
        self.client = service.control.Client('user', token='test-token')
        self.email = fuzzy.FuzzyText(suffix='@example.com').fuzz()

    def test_create_user_minimum_password_length(self):
        response = self.client.call_action(
            'create_user',
            password='s',
            email=self.email,
        )
        self._verify_field_error(response, 'password', 'INVALID_MIN_LENGTH')

    def test_create_user_maximum_password_length(self):
        response = self.client.call_action(
            'create_user',
            password='s' * 100,
            email=self.email,
        )
        self._verify_field_error(response, 'password', 'INVALID_MAX_LENGTH')

    def test_create_user(self):
        response = self.client.call_action(
            'create_user',
            password='a_valid_password',
            email=self.email,
        )
        self.assertTrue(response.success)

        self.assertTrue(uuid.UUID(response.result.user.id, version=4))
        self.assertEqual(
            response.result.user.primary_email,
            self.email,
        )
        self.assertTrue(response.result.user.is_active)
        self.assertFalse(response.result.user.is_admin)

    def test_create_user_no_password(self):
        response = self.client.call_action('create_user', email=self.email)
        self.assertTrue(response.success)

        self.assertEqual(response.result.user.primary_email, self.email)

    def test_create_user_duplicate(self):
        response = self.client.call_action('create_user', email=self.email)
        self.assertTrue(response.success)
        response = self.client.call_action('create_user', email=self.email)
        self.assertFalse(response.success)
        self.assertEqual(response.error_details[0].detail, 'ALREADY_EXISTS')

    def test_get_user(self):
        response = self.client.call_action('create_user', email=self.email)
        self.assertTrue(response.success)

        response = self.client.call_action('get_user', email=self.email)

    def test_update_user_invalid_user_id(self):
        response = self.client.call_action('update_user', user={'id': 'invalid'})
        self._verify_field_error(response, 'user.id')

    def test_update_user_does_not_exist(self):
        response = self.client.call_action('update_user', user={'id': fuzzy.FuzzyUUID().fuzz()})
        self._verify_field_error(response, 'user.id', 'DOES_NOT_EXIST')

    def test_update_user(self):
        user = factories.UserFactory.create_protobuf()
        user.phone_number = '+13109991557'
        response = self.client.call_action('update_user', user=user)
        self.assertTrue(response.success)
        self.assertEqual(user.id, response.result.user.id)
        self.assertEqual(user.phone_number, response.result.user.phone_number)
