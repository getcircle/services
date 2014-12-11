from django.test import TestCase
from service import exceptions

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
            'user_id': self.user.id.hex,
            'type': identity_constants.IDENTITY_TYPE_INTERNAL_NAME,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'email': self.email,
            'phone_number': self.phone_number,
        }

    def test_create_internal_identity(self):
        identity = actions.CreateIdentity(self.data).execute()
        self.assertEqual(identity.first_name, self.first_name)
        self.assertEqual(identity.last_name, self.last_name)
        self.assertEqual(identity.email, self.email)
        self.assertEqual(str(identity.phone_number), self.phone_number)

    def test_create_internal_identity_invalid_data(self):
        with self.assertRaises(exceptions.ValidationError):
            actions.CreateIdentity({
                'user_id': self.user.id.hex,
                'type': None,
                'first_name': 'Michael',
            }).execute()

    def test_unique_identities_based_on_type(self):
        identity1 = actions.CreateIdentity(self.data).execute()
        self.assertTrue(identity1)
        identity2 = actions.CreateIdentity(self.data).execute()
        self.assertIsNone(identity2)
