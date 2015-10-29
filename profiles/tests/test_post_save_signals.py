from mock import patch
from services.test import (
    fuzzy,
    TestCase,
)

from .. import (
    factories,
    models,
)


class TestPostSaveSignals(TestCase):

    @patch('profiles.receivers._update_profile_entity')
    def test_post_save_signal_profile(self, patched):
        instance = factories.ProfileFactory.build()
        instance.save()
        self.assertEqual(patched.call_count, 1)
        call_args = patched.call_args_list[0][0]
        self.assertEqual(call_args, (instance.id, instance.organization_id))
        instance.first_name = fuzzy.FuzzyText().fuzz()
        instance.save()
        self.assertEqual(patched.call_count, 2)

    @patch('profiles.receivers._update_profile_entity')
    def test_post_save_signal_contact_method(self, patched):
        profile = factories.ProfileFactory.create()
        instance = models.ContactMethod(
            profile=profile,
            value='test',
            organization_id=profile.organization_id,
        )
        instance.save()
        self.assertEqual(patched.call_count, 1)
        call_args = patched.call_args_list[0][0]
        self.assertEqual(call_args, (instance.profile_id, instance.organization_id))
        instance.value = fuzzy.FuzzyText().fuzz()
        instance.save()
        self.assertEqual(patched.call_count, 2)
