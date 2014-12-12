from django.test import TestCase
from service import exceptions

from users import factories as user_factories

import identities as identity_constants
from . import actions


class TestIdentityActions(TestCase):

    def setUp(self):
        self.user = user_factories.UserFactory.create()
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
        action = actions.CreateIdentity(self.data)
        response = action.execute()
        identity = response['identity']
        self.assertEqual(identity['email'], self.email)
        self.assertEqual(identity['first_name'], self.first_name)
        self.assertEqual(identity['last_name'], self.last_name)
        self.assertEqual(identity['phone_number'], self.phone_number)
        self.assertEqual(identity['user_id'], str(self.user.id))

    def test_create_internal_identity_invalid_data(self):
        with self.assertRaises(exceptions.ValidationError):
            actions.CreateIdentity({
                'user_id': self.user.id.hex,
                'type': None,
                'first_name': 'Michael',
            }).execute()

    def test_unique_identities_based_on_type(self):
        action = actions.CreateIdentity(self.data)
        response = action.execute()
        self.assertTrue(isinstance(response['identity'], dict))

        action = actions.CreateIdentity(self.data)
        response = action.execute()
        self.assertIsNone(response['identity'])

    def test_get_identity_internal(self):
        actions.CreateIdentity(self.data).execute()
        action = actions.GetIdentity({
            'type': identity_constants.IDENTITY_TYPE_INTERNAL_NAME,
            'key': self.email,
        })
        response = action.execute()
        self.assertTrue(isinstance(response['identity'], dict))

    def test_get_identity_internal_invalid(self):
        action = actions.GetIdentity({
            'type': identity_constants.IDENTITY_TYPE_INTERNAL_NAME,
            'key': self.email,
        })
        response = action.execute()
        self.assertIsNone(response['identity'])
