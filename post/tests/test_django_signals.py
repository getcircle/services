from mock import patch
from services.test import (
    fuzzy,
    TestCase,
)

from .. import factories


class Test(TestCase):

    @patch('service.control')
    def test_post_save_signal(self, patched):
        instance = factories.PostFactory.build()
        instance.save()
        self.assertEqual(patched.call_action.call_count, 1)
        call_args = patched.call_action.call_args_list[0][1]
        self.assertEqual(call_args['action'], 'update_entities')
        self.assertEqual(call_args['ids'], [str(instance.id)])
        instance.title = fuzzy.FuzzyText().fuzz()
        instance.save()
        self.assertEqual(patched.call_action.call_count, 2)

    @patch('service.control')
    def test_post_delete_signal(self, patched):
        instance = factories.PostFactory.create()
        # id won't be available after we call delete
        ids = [str(instance.id)]
        instance.delete()
        self.assertEqual(patched.call_action.call_count, 2)
        call_args = patched.call_action.call_args_list[1][1]
        self.assertEqual(call_args['ids'], ids)
        self.assertEqual(call_args['action'], 'delete_entities')
