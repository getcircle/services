import uuid
from django.test import TestCase

from . import (
    actions,
    models,
)


class TestUserActions(TestCase):

    def test_create_user(self):
        user = actions.create_user()
        self.assertTrue(isinstance(user, models.User))

    def test_user_id_is_uuid(self):
        user = actions.create_user()
        expected_pk = uuid.UUID(hex=user.id.hex, version=4)
        self.assertEqual(user.id, expected_pk)
