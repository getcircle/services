import service.control

from services.test import (
    fuzzy,
    TestCase,
)

from .. import factories


class TestProfileItems(TestCase):

    def setUp(self):
        self.client = service.control.Client('profile', token='test-token')

    def test_add_items_to_profile(self):
        profile = factories.ProfileFactory.create_protobuf()
        item_1 = profile.items.add()
        item_1.key = fuzzy.FuzzyText().fuzz()
        item_1.value = fuzzy.FuzzyText().fuzz()

        item_2 = profile.items.add()
        item_2.key = fuzzy.FuzzyText().fuzz()
        item_2.value = fuzzy.FuzzyText().fuzz()

        response = self.client.call_action('update_profile', profile=profile)
        self.assertEqual(len(response.result.profile.items), 2)

    def test_update_items_on_profile(self):
        profile = factories.ProfileFactory.create_protobuf(items=[('Custom Item', 'Value')])
        another_item = profile.items.add()
        another_item.key = fuzzy.FuzzyText().fuzz()
        another_item.value = fuzzy.FuzzyText().fuzz()
        response = self.client.call_action('update_profile', profile=profile)
        self.assertEqual(len(response.result.profile.items), 2)

        response = self.client.call_action('get_profile', profile_id=profile.id)
        self.assertEqual(len(response.result.profile.items), 2)

    def test_reorder_items_on_profile(self):
        profile = factories.ProfileFactory.create_protobuf(
            items=[('First Item', 'Value'), ('Second Item', 'Value')]
        )
        profile.items.sort(key=lambda x: x.key, reverse=True)
        response = self.client.call_action('update_profile', profile=profile)
        self.assertTrue(response.result.profile.items[0].key.startswith('Second'))

    def test_add_empty_item_to_profile(self):
        profile = factories.ProfileFactory.create_protobuf()
        profile.items.add()
        response = self.client.call_action('update_profile', profile=profile)
        self.assertEqual(len(response.result.profile.items), 0)
