from mock import patch
from services.test import (
    fuzzy,
    TestCase,
)

from .models import TestSearchModel


class TestPostSaveSignals(TestCase):

    @patch('search.receivers.update_index_for_model')
    def test_post_save_signal(self, patched):
        instance = TestSearchModel.objects.create(
            title=fuzzy.FuzzyText().fuzz(),
            content=fuzzy.FuzzyText().fuzz(),
        )
        self.assertEqual(patched.delay.call_count, 1)
        call_args = patched.delay.call_args_list[0][0]
        self.assertEqual(call_args, ('tests', 'testsearchmodel', instance.pk))
        instance.title = fuzzy.FuzzyText().fuzz()
        instance.save()
        self.assertEqual(patched.delay.call_count, 2)
