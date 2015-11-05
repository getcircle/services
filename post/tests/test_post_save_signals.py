from mock import patch
from services.test import (
    fuzzy,
    TestCase,
)

from .. import factories


class TestPostSaveSignals(TestCase):

    @patch('profiles.receivers.service.control')
    def test_post_save_signal_profile(self, patched):
        instance = factories.PostFactory.build()
        instance.save()
        self.assertEqual(patched.call_action.call_count, 1)
        call_args = patched.call_action.call_args_list[0][1]
        self.assertEqual(call_args['ids'], [str(instance.id)])
        instance.title = fuzzy.FuzzyText().fuzz()
        instance.save()
        self.assertEqual(patched.call_action.call_count, 2)
