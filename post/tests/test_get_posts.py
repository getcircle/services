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
        factories.PostFactory.create_batch(size=3, profile=self.profile)
        response = self.client.call_action(
            'get_posts',
            all_states=True,
            by_profile_id=self.profile.id,
        )
        self.assertEqual(len(response.result.posts), 3)

    def test_get_posts_organization_default(self):
        posts = factories.PostFactory.create_batch(size=3, organization_id=self.organization.id)
        factories.PostFactory.create_batch(size=3)
        response = self.client.call_action('get_posts', all_states=True)
        self.assertEqual(len(response.result.posts), len(posts))

    def test_get_posts_specify_by_profile_id(self):
        profile_id = fuzzy.FuzzyUUID().fuzz()
        factories.PostFactory.create_batch(
            size=3,
            organization_id=self.organization.id,
            by_profile_id=profile_id,
        )
        response = self.client.call_action('get_posts', by_profile_id=profile_id, all_states=True)
        self.assertEqual(len(response.result.posts), 3)

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
        )
        # create posts in another organization
        factories.PostFactory.create_batch(size=3)
        response = self.client.call_action(
            'get_posts',
            ids=[str(p.id) for p in posts[:2]],
            all_states=True,
        )
        self.assertEqual(len(response.result.posts), 2)
