import service.control

from services.test import (
    fuzzy,
    mocks,
    MockedTestCase,
)


class TestPosts(MockedTestCase):

    def setUp(self):
        super(TestPosts, self).setUp()
        self.organization = mocks.mock_organization()
        self.profile = mocks.mock_profile(organization_id=self.organization.id)
        token = mocks.mock_token(organization_id=self.organization.id, profile_id=self.profile.id)
        self.client = service.control.Client('post', token=token)
        self.mock.instance.dont_mock_service('post')

    def test_create_post_post_required(self):
        with self.assertFieldError('post', 'MISSING'):
            self.client.call_action('create_post')

    def test_create_post(self):
        post_title = 'some title'
        post_content = 'some text'
        response = self.client.call_action('create_post', post={
            'title': post_title,
            'content': post_content,
        })
        post = response.result.post
        self.assertEqual(post_title, post.title)
        self.assertEqual(post_content, post.content)
        self.assertEqual(self.profile.id, post.by_profile_id)
        self.assertEqual(self.organization.id, post.organization_id)

    def test_create_post_specified_by_profile_id_rejected(self):
        post = {'title': 'title', 'content': 'content', 'by_profile_id': fuzzy.FuzzyUUID().fuzz()}
        response = self.client.call_action('create_post', post=post)
        self.assertEqual(response.result.post.by_profile_id, self.profile.id)

    def test_create_post_specified_organization_id_rejected(self):
        post = {'title': 'title', 'content': 'content', 'organization_id': fuzzy.FuzzyUUID().fuzz()}
        response = self.client.call_action('create_post', post=post)
        self.assertEqual(response.result.post.organization_id, self.organization.id)

    def test_create_post_title_required(self):
        with self.assertFieldError('post.title', 'MISSING'):
            self.client.call_action('create_post', post={'content': 'some content'})

    def test_create_post_content_required(self):
        with self.assertFieldError('post.content', 'MISSING'):
            self.client.call_action('create_post', post={'title': 'title'})
