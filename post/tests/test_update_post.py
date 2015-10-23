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

    def test_update_post_post_required(self):
        with self.assertFieldError('post', 'MISSING'):
            self.client.call_action('update_post')

    def test_update_post(self):
        updated_title = fuzzy.FuzzyText().fuzz()
        updated_content = fuzzy.FuzzyText().fuzz()

        post = factories.PostFactory.create_protobuf(profile=self.profile)
        post.title = updated_title
        post.content = updated_content
        response = self.client.call_action('update_post', post=post)
        post = response.result.post
        self.assertEqual(updated_title, post.title)
        self.assertEqual(updated_content, post.content)
        self.assertEqual(self.profile.id, post.by_profile_id)
        self.assertEqual(self.organization.id, post.organization_id)

    def test_update_post_does_not_exist(self):
        post = factories.PostFactory.build_protobuf()
        with self.assertFieldError('post.id', 'DOES_NOT_EXIST'):
            self.client.call_action('update_post', post=post)

    def test_update_post_ignore_organization_id_profile_id(self):
        post = factories.PostFactory.create_protobuf(profile=self.profile)
        post.by_profile_id = fuzzy.FuzzyUUID().fuzz()
        post.organization_id = fuzzy.FuzzyUUID().fuzz()
        post.title = 'new'
        response = self.client.call_action('update_post', post=post)
        updated_post = response.result.post
        self.assertEqual(updated_post.title, post.title)
        self.assertEqual(updated_post.by_profile_id, self.profile.id)
        self.assertEqual(updated_post.organization_id, self.organization.id)

    def test_update_post_title_required(self):
        post = factories.PostFactory.build_protobuf(profile=self.profile)
        post.ClearField('title')
        with self.assertFieldError('post.title', 'MISSING'):
            self.client.call_action('update_post', post=post)

    def test_update_post_content_required(self):
        post = factories.PostFactory.build_protobuf(profile=self.profile)
        post.ClearField('content')
        with self.assertFieldError('post.content', 'MISSING'):
            self.client.call_action('update_post', post=post)

    def test_update_post_post_id_required(self):
        post = factories.PostFactory.build_protobuf(profile=self.profile)
        post.ClearField('id')
        with self.assertFieldError('post.id', 'MISSING'):
            self.client.call_action('update_post', post=post)

    def test_update_post_invalid_post_id(self):
        post = factories.PostFactory.build_protobuf(id='invalid', profile=self.profile)
        with self.assertFieldError('post.id'):
            self.client.call_action('update_post', post=post)

    def test_update_post_title_empty_string(self):
        post = factories.PostFactory.create_protobuf(profile=self.profile)
        post.title = ''
        with self.assertFieldError('post.title', 'MISSING'):
            self.client.call_action('update_post', post=post)

    def test_update_post_content_empty_string(self):
        post = factories.PostFactory.create_protobuf(profile=self.profile)
        post.content = ''
        with self.assertFieldError('post.content', 'MISSING'):
            self.client.call_action('update_post', post=post)
