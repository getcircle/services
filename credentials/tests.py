from django.test import TestCase

from users.factories import UserFactory

from . import actions
from .factories import CredentialFactory
from .models import Credential

TEST_PASSWORD = 'password'


class TestCredentials(TestCase):

    def setUp(self):
        self.credential = CredentialFactory.create()

    def test_set_password_stores_password_hash(self):
        self.credential.set_password(TEST_PASSWORD)
        self.assertNotEqual(self.credential.password, TEST_PASSWORD)

    def test_check_password_verifies_valid_password(self):
        self.credential.set_password(TEST_PASSWORD)
        self.assertFalse(self.credential.check_password('invalid'))
        self.assertTrue(self.credential.check_password(TEST_PASSWORD))

    def test_set_password_supports_no_commit(self):
        self.credential.set_password(TEST_PASSWORD, commit=False)
        credential = Credential.objects.get(pk=self.credential.pk)
        self.assertIsNone(credential.password)
        self.assertIsNotNone(self.credential.password)


class TestCredentialActions(TestCase):

    def setUp(self):
        self.user = UserFactory.create()

    def test_create_credentials(self):
        created = actions.CreateCredentials({
            'user_id': self.user.id.hex,
            'password': TEST_PASSWORD,
        }).execute()
        self.assertTrue(created)

    def test_verify_credentials(self):
        actions.CreateCredentials({
            'user_id': self.user.id.hex,
            'password': TEST_PASSWORD,
        }).execute()
        valid = actions.VerifyCredentials({
            'user_id': self.user.id.hex,
            'password': TEST_PASSWORD,
        }).execute()
        self.assertTrue(valid)

    def test_update_credentials(self):
        actions.CreateCredentials({
            'user_id': self.user.id.hex,
            'password': TEST_PASSWORD,
        }).execute()

        # try updating with invalid password
        success = actions.UpdateCredentials({
            'user_id': self.user.id.hex,
            'current_password': 'invalid',
            'new_password': 'newpassword',
        }).execute()
        self.assertFalse(success)
        # verify the password wasn't updated
        success = actions.VerifyCredentials({
            'user_id': self.user.id.hex,
            'password': TEST_PASSWORD,
        }).execute()
        self.assertTrue(success)

        # update the password with valid password
        success = actions.UpdateCredentials({
            'user_id': self.user.id.hex,
            'current_password': TEST_PASSWORD,
            'new_password': 'newpassword',
        }).execute()
        self.assertTrue(success)
        # verify the password was updated
        success = actions.VerifyCredentials({
            'user_id': self.user.id.hex,
            'password': 'newpassword',
        })
        self.assertTrue(success)
