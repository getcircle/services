from mock import patch
from protobufs.services.search.containers import entity_pb2
from services.test import (
    fuzzy,
    TestCase,
)

from .. import factories


class TestPostSaveSignals(TestCase):

    @patch('profiles.receivers.update_entity')
    def test_post_save_signal_profile(self, patched):
        instance = factories.ProfileFactory.build()
        instance.save()
        self.assertEqual(patched.call_count, 1)
        call_args = patched.call_args_list[0][0]
        self.assertEqual(call_args, (instance.id, instance.organization_id, entity_pb2.PROFILE))
        instance.first_name = fuzzy.FuzzyText().fuzz()
        instance.save()
        self.assertEqual(patched.call_count, 2)
