from django.test import TestCase

from .factories import CredentialFactory
from .models import Credential


class TestCredentials(TestCase):

    def setUp(self):
        self.credential = CredentialFactory.create()
        self.test_password = 'password'

    def test_set_password_stores_password_hash(self):
        self.credential.set_password(self.test_password)
        self.assertNotEqual(self.credential.password, self.test_password)

    def test_check_password_verifies_valid_password(self):
        self.credential.set_password(self.test_password)
        self.assertFalse(self.credential.check_password('invalid'))
        self.assertTrue(self.credential.check_password(self.test_password))

    def test_set_password_supports_no_commit(self):
        self.credential.set_password(self.test_password, commit=False)
        credential = Credential.objects.get(pk=self.credential.pk)
        self.assertIsNone(credential.password)
        self.assertIsNotNone(self.credential.password)
