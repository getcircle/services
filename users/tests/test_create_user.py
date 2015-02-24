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
        with self.assertFieldError('password', 'INVALID_MIN_LENGTH'):
            self.client.call_action(
                'create_user',
                password='s',
                email=self.email,
            )

    def test_create_user_maximum_password_length(self):
        with self.assertFieldError('password', 'INVALID_MAX_LENGTH'):
            self.client.call_action(
                'create_user',
                password='s' * 100,
                email=self.email,
            )

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
        self.assertFalse(response.result.user.HasField('password'))

    def test_create_user_no_password(self):
        response = self.client.call_action('create_user', email=self.email)
        self.assertTrue(response.success)

        self.assertEqual(response.result.user.primary_email, self.email)

    def test_create_user_duplicate(self):
        response = self.client.call_action('create_user', email=self.email)
        self.assertTrue(response.success)

        with self.assertRaises(self.client.CallActionError) as expected:
            self.client.call_action('create_user', email=self.email)
        response = expected.exception.response
        self.assertEqual(response.error_details[0].detail, 'ALREADY_EXISTS')

    def test_get_user(self):
        response = self.client.call_action('create_user', email=self.email)
        self.assertTrue(response.success)

        response = self.client.call_action('get_user', email=self.email)

    def test_update_user_invalid_user_id(self):
        with self.assertFieldError('user.id'):
            self.client.call_action('update_user', user={'id': 'invalid'})

    def test_update_user_does_not_exist(self):
        with self.assertFieldError('user.id', 'DOES_NOT_EXIST'):
            self.client.call_action('update_user', user={'id': fuzzy.FuzzyUUID().fuzz()})

    def test_update_user(self):
        user = factories.UserFactory.create_protobuf()
        user.phone_number = '+13109991557'
        response = self.client.call_action('update_user', user=user)
        self.assertTrue(response.success)
        self.assertEqual(user.id, response.result.user.id)
        self.assertEqual(user.phone_number, response.result.user.phone_number)
