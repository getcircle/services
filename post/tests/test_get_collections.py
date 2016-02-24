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

    def test_get_collections_owner_id_invalid(self):
        with self.assertFieldError('owner_id'):
            self.client.call_action('get_collections', owner_id=fuzzy.text())

    def test_get_collections_owned_by_team_wrong_organization(self):
        team = mocks.mock_team()
        factories.CollectionFactory.create_batch(size=3, team=team)
        response = self.client.call_action(
            'get_collections',
            owner_id=team.id,
            owner_type=post_containers.CollectionV1.TEAM,
        )
        self.assertFalse(response.result.collections)

    def test_get_collections_owned_by_profile_wrong_organization(self):
        profile = mocks.mock_profile()
        factories.CollectionFactory.create_batch(size=3, profile=profile)
        response = self.client.call_action(
            'get_collections',
            owner_id=profile.id,
            owner_type=post_containers.CollectionV1.PROFILE,
        )
        self.assertFalse(response.result.collections)

    def test_get_collections_owned_by_team(self):
        team = mocks.mock_team(organization_id=self.organization.id)
        collections = factories.CollectionFactory.create_batch(size=3, team=team)
        for collection in collections:
            factories.CollectionItemFactory.reset_sequence()
            # Add 10 items per collection
            factories.CollectionItemFactory.create_batch(size=10, collection=collection)

        response = self.client.call_action(
            'get_collections',
            owner_id=team.id,
            owner_type=post_containers.CollectionV1.TEAM,
        )
        response_collections = response.result.collections
        self.assertEqual(len(response_collections), len(collections))
        for collection in response_collections:
            self.assertEqual(len(collection.items), 0)
            self.assertEqual(collection.total_items, 10)

    def test_get_collections_owned_by_team_inflate_posts(self):
        team = mocks.mock_team(organization_id=self.organization.id)
        collections = factories.CollectionFactory.create_batch(size=3, team=team)
        for collection in collections:
            posts = factories.PostFactory.create_batch(
                size=10,
                organization_id=self.organization.id,
            )
            for post in posts:
                factories.CollectionItemFactory.create(
                    collection=collection,
                    source=post_containers.CollectionItemV1.LUNO,
                    source_id=str(post.id),
                )

        response = self.client.call_action(
            'get_collections',
            owner_id=team.id,
            owner_type=post_containers.CollectionV1.TEAM,
            items_per_collection=3,
        )
        response_collections = response.result.collections
        self.assertEqual(len(response_collections), len(collections))
        for collection in response_collections:
            self.assertEqual(len(collection.items), 3)
            self.assertEqual(collection.total_items, 10)
            for item in collection.items:
                self.assertEqual(item.source_id, item.post.id)
                self.assertTrue(item.post.title)
                self.assertTrue(item.post.content)

    def test_get_collections_owned_by_team_restrict_post_fields_and_inflations(self):
        team = mocks.mock_team(organization_id=self.organization.id)
        collections = factories.CollectionFactory.create_batch(size=3, team=team)
        for collection in collections:
            posts = factories.PostFactory.create_batch(
                size=10,
                organization_id=self.organization.id,
            )
            for post in posts:
                factories.CollectionItemFactory.create(
                    collection=collection,
                    source=post_containers.CollectionItemV1.LUNO,
                    source_id=str(post.id),
                )

        response = self.client.call_action(
            'get_collections',
            owner_id=team.id,
            owner_type=post_containers.CollectionV1.TEAM,
            items_per_collection=3,
            inflations={'only': ['total_items']},
            fields={
                'only': [
                    '[]collections.[]items.source_id',
                    '[]collections.[]items.post.id',
                    '[]collections.[]items.post.title',
                    '[]collections.[]items.post.created',
                ],
            },
        )
        response_collections = response.result.collections
        self.assertEqual(len(response_collections), len(collections))
        for collection in response_collections:
            self.assertEqual(len(collection.items), 3)
            self.assertEqual(collection.total_items, 10)
            for item in collection.items:
                self.assertEqual(item.source_id, item.post.id)
                self.assertTrue(item.post.title)
                self.assertTrue(item.post.created)
                self.assertFalse(item.post.content)

    def test_get_collections_owned_by_profile(self):
        profile = mocks.mock_profile(organization_id=self.organization.id)
        collections = factories.CollectionFactory.create_batch(size=3, profile=profile)
        response = self.client.call_action(
            'get_collections',
            owner_id=profile.id,
            owner_type=post_containers.CollectionV1.PROFILE,
        )
        self.assertEqual(len(response.result.collections), len(collections))

    def test_get_collections_for_post_id(self):
        post = factories.PostFactory.create(organization_id=self.organization.id)
        items = factories.CollectionItemFactory.create_batch(
            size=5,
            organization_id=self.organization.id,
            collection__organization_id=self.organization.id,
            source=post_containers.CollectionItemV1.LUNO,
            source_id=str(post.id),
        )
        response = self.client.call_action(
            'get_collections',
            source=post_containers.CollectionItemV1.LUNO,
            source_id=str(post.id),
            inflations={'disabled': True},
        )
        self.assertEqual(len(response.result.collections), len(items))
        for collection in response.result.collections:
            self.assertFalse(collection.items)

    def test_get_collections_for_post_id_wrong_organization(self):
        post = factories.PostFactory.create()
        factories.CollectionItemFactory.create_batch(
            size=5,
            organization_id=post.organization_id,
            collection__organization_id=post.organization_id,
            source=post_containers.CollectionItemV1.LUNO,
            source_id=str(post.id),
        )
        response = self.client.call_action(
            'get_collections',
            source=post_containers.CollectionItemV1.LUNO,
            source_id=str(post.id),
            inflations={'disabled': True},
        )
        self.assertFalse(response.result.collections)

    def test_get_collections_owned_by_profile_is_default(self):
        profile = mocks.mock_profile(organization_id=self.organization.id)
        factories.CollectionFactory.create_batch(size=3, profile=profile)
        factories.CollectionFactory.create(profile=profile, is_default=True)
        response = self.client.call_action(
            'get_collections',
            owner_id=profile.id,
            owner_type=post_containers.CollectionV1.PROFILE,
            is_default=True
        )
        self.assertEqual(len(response.result.collections), 1)
        collection = response.result.collections[0]
        self.assertTrue(collection.is_default)

    def test_get_collections_owned_by_team_is_default(self):
        team = mocks.mock_team(organization_id=self.organization.id)
        factories.CollectionFactory.create_batch(size=3, team=team)
        factories.CollectionFactory.create(team=team, is_default=True)
        response = self.client.call_action(
            'get_collections',
            owner_id=team.id,
            owner_type=post_containers.CollectionV1.TEAM,
            is_default=True
        )
        self.assertEqual(len(response.result.collections), 1)
        collection = response.result.collections[0]
        self.assertTrue(collection.is_default)

    def test_get_collections_owned_by_profile_paginated(self):
        profile = mocks.mock_profile(organization_id=self.organization.id)
        factories.CollectionFactory.create_batch(size=30, profile=profile)
        response = self.client.call_action(
            'get_collections',
            owner_id=profile.id,
            owner_type=post_containers.CollectionV1.PROFILE,
        )
        self.assertEqual(len(response.result.collections), 15)

    def test_get_collections_for_organization(self):
        expected = factories.CollectionFactory.create_batch(
            size=2,
            organization_id=self.organization.id,
        )
        factories.CollectionFactory.create_batch(size=5)
        response = self.client.call_action('get_collections')
        self.assertEqual(len(response.result.collections), len(expected))
        for collection in response.result.collections:
            self.assertEqual(collection.organization_id, self.organization.id)

    def test_get_collections_by_ids_wrong_organization(self):
        collections = factories.CollectionFactory.create_batch(size=2)
        response = self.client.call_action('get_collections', ids=[str(c.id) for c in collections])
        self.assertEqual(len(response.result.collections), 0)

    def test_get_collections_by_ids(self):
        expected = factories.CollectionFactory.create_batch(
            size=2,
            organization_id=self.organization.id,
        )
        factories.CollectionFactory.create_batch(size=2, organization_id=self.organization.id)
        response = self.client.call_action('get_collections', ids=[str(c.id) for c in expected])
        self.assertEqual(len(response.result.collections), len(expected))

    def test_get_collections_by_ids_invalid_ids(self):
        with self.assertFieldError('ids'):
            self.client.call_action('get_collections', ids=['invalid', 'invalid'])
