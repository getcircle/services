from django.test import TestCase

from . import (
    actions,
    models,
)


class TestUserActions(TestCase):

    def test_create_user(self):
        user = actions.create_user()
        self.assertTrue(isinstance(user, models.User))
