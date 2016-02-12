from protobufs.services.post import containers_pb2 as post_containers
import service.control

from services.test import (
    fuzzy,
    mocks,
    MockedTestCase,
)

from .. import factories


class Test(MockedTestCase):

    def setUp(self):
        super(Test, self).setUp()
        self.organization = mocks.mock_organization()
        self.profile = mocks.mock_profile(organization_id=self.organization.id)
        self.team = mocks.mock_team(organization_id=self.organization.id)
        token = mocks.mock_token(organization_id=self.organization.id, profile_id=self.profile.id)
        self.client = service.control.Client('post', token=token)
        self.mock.instance.dont_mock_service('post')

        factories.CollectionItemFactory.reset_sequence()

    def test_get_collection_items_collection_id_required(self):
        with self.assertFieldError('collection_id', 'MISSING'):
            self.client.call_action('get_collection_items')

    def test_get_collection_items_collection_id_invalid(self):
        with self.assertFieldError('collection_id'):
            self.client.call_action('get_collection_items', collection_id=fuzzy.text())

    def test_get_collection_items_collection_id_does_not_exist(self):
        with self.assertFieldError('collection_id', 'DOES_NOT_EXIST'):
            self.client.call_action('get_collection_items', collection_id=fuzzy.uuid())

    def test_get_collection_items_wrong_organization(self):
        collection = factories.CollectionFactory.create_protobuf()
        with self.assertFieldError('collection_id', 'DOES_NOT_EXIST'):
            self.client.call_action('get_collection_items', collection_id=collection.id)

    def test_get_collection_items(self):
        collection = factories.CollectionFactory.create(profile=self.profile)
        posts = factories.PostFactory.create_batch(
            size=10,
            organization_id=self.organization.id,
        )
        items_dict = {}
        for post in posts:
            item = factories.CollectionItemFactory.create(
                collection=collection,
                source=post_containers.CollectionItemV1.LUNO,
                source_id=str(post.id),
            )
            items_dict[str(item.id)] = {'item': item, 'post': post}

        response = self.client.call_action(
            'get_collection_items',
            collection_id=str(collection.id),
        )
        self.assertEqual(len(response.result.items), 10)
        for item in response.result.items:
            expected_item = items_dict[item.id]['item']
            expected_post = items_dict[item.id]['post']

            self.assertEqual(str(expected_item.id), item.id)
            self.assertEqual(expected_item.source, item.source)
            self.assertEqual(expected_item.source_id, item.source_id)
            self.assertEqual(item.post.id, str(expected_post.id))
            self.assertEqual(item.post.title, expected_post.title)
            self.assertEqual(item.post.content, expected_post.content)

    def test_get_collection_items_restrict_post_fields_and_inflations(self):
        collection = factories.CollectionFactory.create(profile=self.profile)
        posts = factories.PostFactory.create_batch(
            size=10,
            organization_id=self.organization.id,
        )
        items_dict = {}
        for post in posts:
            item = factories.CollectionItemFactory.create(
                collection=collection,
                source=post_containers.CollectionItemV1.LUNO,
                source_id=str(post.id),
            )
            items_dict[str(item.id)] = {'item': item, 'post': post}

        response = self.client.call_action(
            'get_collection_items',
            collection_id=str(collection.id),
            fields={'exclude': ['post.content']},
            inflations={'disabled': True},
        )
        self.assertEqual(len(response.result.items), 10)
        for index, item in enumerate(response.result.items):
            expected_item = items_dict[item.id]['item']
            expected_post = items_dict[item.id]['post']

            self.assertEqual(item.position, index)
            self.assertEqual(str(expected_item.id), item.id)
            self.assertEqual(expected_item.source, item.source)
            self.assertEqual(expected_item.source_id, item.source_id)
            self.assertEqual(item.post.id, str(expected_post.id))
            self.assertEqual(item.post.title, expected_post.title)
            self.assertFalse(item.post.content)
