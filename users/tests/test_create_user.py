import uuid

import service.control

from services.test import (
    fuzzy,
    TestCase,
)
from services.token import make_admin_token


class TestUserActions(TestCase):

    def setUp(self):
        self.organization_id = fuzzy.uuid()
        token = make_admin_token(organization_id=self.organization_id)
        self.client = service.control.Client('user', token=token)
        self.email = fuzzy.FuzzyText(suffix='@example.com').fuzz()

    def test_create_user_minimum_password_length(self):
        with self.assertFieldError('password', 'INVALID_MIN_LENGTH'):
            self.client.call_action(
                'create_user',
                password='s',
                email=self.email,
                organization_id=self.organization_id,
            )

    def test_create_user_maximum_password_length(self):
        with self.assertFieldError('password', 'INVALID_MAX_LENGTH'):
            self.client.call_action(
                'create_user',
                password='s' * 100,
                email=self.email,
                organization_id=self.organization_id,
            )

    def test_create_user(self):
        response = self.client.call_action(
            'create_user',
            password='a_valid_password',
            email=self.email,
            organization_id=self.organization_id,
        )
        self.assertTrue(response.success)

        user = response.result.user
        self.assertTrue(uuid.UUID(user.id, version=4))
        self.assertEqual(user.primary_email, self.email)
        self.assertEqual(user.organization_id, self.organization_id)
        self.assertTrue(response.result.user.is_active)
        self.assertFalse(response.result.user.is_admin)
        self.assertFalse(response.result.user.password)

    def test_create_user_no_password(self):
        response = self.client.call_action(
            'create_user',
            email=self.email,
            organization_id=self.organization_id,
        )
        self.assertTrue(response.success)

        user = response.result.user
        self.assertEqual(user.primary_email, self.email)
        self.assertEqual(user.organization_id, self.organization_id)

    def test_create_user_duplicate(self):
        response = self.client.call_action(
            'create_user',
            email=self.email,
            organization_id=self.organization_id,
        )
        self.assertTrue(response.success)

        with self.assertRaises(service.control.CallActionError) as expected:
            self.client.call_action(
                'create_user',
                email=self.email,
                organization_id=self.organization_id,
            )

        response = expected.exception.response
        self.assertEqual(response.error_details[0].detail, 'ALREADY_EXISTS')

    def test_create_user_duplicate_email_different_organization(self):
        organization_id_1 = fuzzy.uuid()
        organization_id_2 = fuzzy.uuid()
        response = self.client.call_action(
            'create_user',
            email=self.email,
            organization_id=organization_id_1,
        )
        user_1 = response.result.user
        self.assertEqual(user_1.organization_id, organization_id_1)
        self.assertEqual(user_1.primary_email, self.email)

        response = self.client.call_action(
            'create_user',
            email=self.email,
            organization_id=organization_id_2,
        )
        user_2 = response.result.user
        self.assertEqual(user_2.organization_id, organization_id_2)
        self.assertEqual(user_2.primary_email, self.email)
        self.assertNotEqual(user_1.id, user_2.id)
        self.assertNotEqual(user_1.organization_id, user_2.organization_id)

    def test_get_user(self):
        response = self.client.call_action(
            'create_user',
            email=self.email,
            organization_id=self.organization_id,
        )
        self.assertTrue(response.success)
        response = self.client.call_action('get_user', email=self.email)

    def test_bulk_create_users(self):
        users = []
        for _ in range(3):
            users.append({
                'primary_email': fuzzy.FuzzyText(suffix='@example.com').fuzz(),
                'password': fuzzy.FuzzyText().fuzz(),
                # this organization_id should be ignored
                'organization_id': fuzzy.uuid(),
            })

        response = self.client.call_action(
            'bulk_create_users',
            users=users,
            organization_id=self.organization_id,
        )
        self.assertEqual(len(response.result.users), len(users))
        for user in response.result.users:
            self.assertEqual(user.organization_id, self.organization_id)

    def test_bulk_create_users_users_required(self):
        with self.assertFieldError('users', 'MISSING'):
            self.client.call_action('bulk_create_users', organization_id=self.organization_id)

    def test_bulk_create_users_organization_id_required(self):
        with self.assertFieldError('organization_id', 'MISSING'):
            self.client.call_action('bulk_create_users', users=[{'primary_email': 'email'}])
