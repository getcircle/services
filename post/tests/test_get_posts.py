from protobufs.services.post import containers_pb2 as post_containers
import service.control

from services.test import (
    fuzzy,
    mocks,
    MockedTestCase,
)

from .. import factories


class TestPosts(MockedTestCase):

    def setUp(self):
        super(TestPosts, self).setUp()
        self.organization = mocks.mock_organization()
        self.profile = mocks.mock_profile(organization_id=self.organization.id)
        token = mocks.mock_token(organization_id=self.organization.id, profile_id=self.profile.id)
        self.client = service.control.Client('post', token=token)
        self.mock.instance.dont_mock_service('post')

    def test_get_posts_current_user(self):
        # create posts in all different states
        factories.PostFactory.create(profile=self.profile, state=post_containers.LISTED)
        factories.PostFactory.create(profile=self.profile, state=post_containers.UNLISTED)
        factories.PostFactory.create(profile=self.profile, state=post_containers.DRAFT)

        response = self.client.call_action(
            'get_posts',
            all_states=True,
            by_profile_id=self.profile.id,
        )
        self.assertEqual(len(response.result.posts), 3)

        response = self.client.call_action(
            'get_posts',
            state=post_containers.DRAFT,
            by_profile_id=self.profile.id,
        )
        self.assertEqual(len(response.result.posts), 1)
        self.assertEqual(response.result.posts[0].state, post_containers.DRAFT)

    def test_get_posts_organization_default(self):
        factories.PostFactory.create_batch(
            size=2,
            organization_id=self.organization.id,
            state=post_containers.DRAFT,
        )
        listed_posts = factories.PostFactory.create_batch(
            size=2,
            organization_id=self.organization.id,
            state=post_containers.LISTED,
        )
        factories.PostFactory.create_batch(
            size=2,
            organization_id=self.organization.id,
            state=post_containers.UNLISTED,
        )
        factories.PostFactory.create_batch(size=3)
        response = self.client.call_action('get_posts', all_states=True)
        self.assertEqual(len(response.result.posts), len(listed_posts))

    def test_get_posts_wrong_organization(self):
        profile_id = fuzzy.FuzzyUUID().fuzz()
        factories.PostFactory.create_batch(size=3, by_profile_id=profile_id)
        response = self.client.call_action('get_posts', by_profile_id=profile_id, all_states=True)
        self.assertEqual(len(response.result.posts), 0)

    def test_get_posts_states(self):

        factories.PostFactory.create_batch(
            size=2,
            profile=self.profile,
            state=post_containers.DRAFT,
        )
        factories.PostFactory.create_batch(
            size=2,
            profile=self.profile,
            state=post_containers.LISTED,
        )
        factories.PostFactory.create_batch(
            size=2,
            profile=self.profile,
            state=post_containers.UNLISTED,
        )

        def _verify_posts_with_state(state, expected_num):
            response = self.client.call_action('get_posts', state=state)
            posts = response.result.posts
            self.assertEqual(len(posts), expected_num)
            self.assertTrue(all([p.state == state for p in posts]))

        _verify_posts_with_state(post_containers.DRAFT, 2)
        _verify_posts_with_state(post_containers.LISTED, 2)
        _verify_posts_with_state(post_containers.UNLISTED, 2)

    def test_get_posts_with_ids(self):
        posts = factories.PostFactory.create_batch(
            size=3,
            organization_id=self.organization.id,
            state=post_containers.LISTED,
        )
        # create unlisted posts
        factories.PostFactory.create(
            organization_id=self.organization.id,
            state=post_containers.UNLISTED,
        )
        factories.PostFactory.create(
            organization_id=self.organization.id,
            state=post_containers.DRAFT,
        )
        # create posts in another organization
        factories.PostFactory.create_batch(size=3)
        response = self.client.call_action(
            'get_posts',
            ids=[str(p.id) for p in posts[:2]],
            all_states=True,
        )
        self.assertEqual(len(response.result.posts), 2)

    def test_get_posts_only_return_listed(self):
        profile = mocks.mock_profile(organization_id=self.organization.id)
        factories.PostFactory.create(
            profile=profile,
            state=post_containers.UNLISTED,
        )
        factories.PostFactory.create(
            profile=profile,
            state=post_containers.LISTED,
        )
        factories.PostFactory.create(
            profile=profile,
            state=post_containers.DRAFT,
        )

        response = self.client.call_action('get_posts', by_profile_id=profile.id, all_states=True)
        self.assertEqual(len(response.result.posts), 1)

        with self.assertRaisesCallActionError() as expected:
            self.client.call_action(
                'get_posts',
                by_profile_id=profile.id,
                state=post_containers.DRAFT,
            )

        self.assertIn('PERMISSION_DENIED', expected.exception.response.errors)

        with self.assertRaisesCallActionError() as expected:
            self.client.call_action(
                'get_posts',
                by_profile_id=profile.id,
                state=post_containers.UNLISTED,
            )

        self.assertIn('PERMISSION_DENIED', expected.exception.response.errors)

        response = self.client.call_action('get_posts', all_states=True)
        self.assertEqual(len(response.result.posts), 1)
