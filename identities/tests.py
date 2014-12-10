from django.test import TestCase

from users import actions as user_actions

import identities as identity_constants
from . import actions


class TestIdentityActions(TestCase):

    def setUp(self):
        self.user = user_actions.create_user()
        self.first_name = 'Michael'
        self.last_name = 'Hahn'
        self.email = 'mwhahn@gmail.com'
        self.phone_number = '+19492933322'
        self.data = {
            'first_name': self.first_name,
            'last_name': self.last_name,
            'email': self.email,
            'phone_number': self.phone_number,
        }

    def test_create_internal_identity(self):
        identity = actions.create_identity(
            user_id=self.user.id.hex,
            identity_type=identity_constants.IDENTITY_TYPE_INTERNAL_NAME,
            data=self.data
        )
        self.assertEqual(identity.first_name, self.first_name)
        self.assertEqual(identity.last_name, self.last_name)
        self.assertEqual(identity.email, self.email)
        self.assertEqual(str(identity.phone_number), self.phone_number)

    def test_create_internal_identity_invalid_data(self):
        identity = actions.create_identity(
            user_id=self.user.id.hex,
            identity_type=None,
            data={
                'first_name': 'Michael',
            },
        )
        self.assertIsNone(identity)

    def test_unique_identities_based_on_type(self):
        actions.create_identity(
            user_id=self.user.id.hex,
            identity_type=identity_constants.IDENTITY_TYPE_INTERNAL_NAME,
            data=self.data,
        )
        identity = actions.create_identity(
            user_id=self.user.id.hex,
            identity_type=identity_constants.IDENTITY_TYPE_INTERNAL_NAME,
            data=self.data,
        )
        self.assertIsNone(identity)
