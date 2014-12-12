import uuid
from django.test import TestCase
from service import exceptions

from . import (
    actions,
    factories,
)


class TestUserActions(TestCase):

    def test_user_id_is_uuid(self):
        action = actions.CreateUser()
        action.execute()
        expected_pk = uuid.UUID(hex=action.user_id, version=4)
        self.assertEqual(action.user_id, expected_pk.hex)

    def test_actions_valid_user(self):
        expected_user = factories.UserFactory.create()
        action = actions.ValidUser({'user_id': expected_user.id.hex})
        action.execute()
        self.assertTrue(action.exists)

        with self.assertRaises(exceptions.ConversionError):
            actions.ValidUser({'user_id': 'invalid'})

        action = actions.ValidUser({'user_id': uuid.uuid4().hex})
        action.execute()
        self.assertFalse(action.exists)
