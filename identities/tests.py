from django.test import TestCase

from users import actions as user_actions

from . import actions


class TestIdentityActions(TestCase):

    def setUp(self):
        self.user = user_actions.create_user()

    def test_create_internal_identity(self):
        first_name = 'Michael'
        last_name = 'Hahn'
        email = 'mwhahn@gmail.com'
        phone_number = '+19492933322'
        identity = actions.create_identity(
            user_id=self.user.id.hex,
            identity_type='internal',
            data={
                'first_name': first_name,
                'last_name': last_name,
                'email': email,
                'phone_number': phone_number,
            },
        )
        self.assertEqual(identity.first_name, first_name)
        self.assertEqual(identity.last_name, last_name)
        self.assertEqual(identity.email, email)
        self.assertEqual(str(identity.phone_number), phone_number)

    def test_create_internal_identity_invalid_data(self):
        identity = actions.create_identity(
            user_id=self.user.id.hex,
            identity_type=None,
            data={
                'first_name': 'Michael',
            },
        )
        self.assertIsNone(identity)
