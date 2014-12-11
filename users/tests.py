import uuid
from django.test import TestCase
from service import exceptions

from . import (
    actions,
    models,
)


class TestUserActions(TestCase):

    def test_actions_create_user(self):
        user = actions.CreateUser().execute()
        self.assertTrue(isinstance(user, models.User))

    def test_user_id_is_uuid(self):
        user = actions.CreateUser().execute()
        expected_pk = uuid.UUID(hex=user.id.hex, version=4)
        self.assertEqual(user.id, expected_pk)

    def test_actions_get_user(self):
        expected_user = actions.CreateUser().execute()
        user = actions.GetUser({'user_id': expected_user.id.hex}).execute()
        self.assertEqual(user, expected_user)

    def test_actions_valid_user(self):
        expected_user = actions.CreateUser().execute()
        valid = actions.ValidUser({'user_id': expected_user.id.hex}).execute()
        self.assertTrue(valid)

        with self.assertRaises(exceptions.ConversionError):
            actions.ValidUser({'user_id': 'invalid'})

        valid = actions.ValidUser({'user_id': uuid.uuid4().hex}).execute()
        self.assertFalse(valid)
