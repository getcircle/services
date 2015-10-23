import service.control

from services.test import (
    fuzzy,
    mocks,
    MockedTestCase,
)

from .. import (
    factories,
    models,
)


class TestDeletePosts(MockedTestCase):

    def setUp(self):
        super(TestDeletePosts, self).setUp()
        self.organization = mocks.mock_organization()
        self.profile = mocks.mock_profile(organization_id=self.organization.id)
        token = mocks.mock_token(organization_id=self.organization.id, profile_id=self.profile.id)
        self.client = service.control.Client('post', token=token)
        self.mock.instance.dont_mock_service('post')

    def test_delete_post_id_required(self):
        with self.assertFieldError('id', 'MISSING'):
            self.client.call_action('delete_post')

    def test_delete_post_invalid_id(self):
        with self.assertFieldError('id'):
            self.client.call_action('delete_post', id='invalid')

    def test_delete_post_not_author_rejected(self):
        post = factories.PostFactory.create_protobuf(organization_id=self.organization.id)
        with self.assertRaisesCallActionError() as expected:
            self.client.call_action('delete_post', id=post.id)
        self.assertIn('PERMISSION_DENIED', expected.exception.response.errors)

    def test_delete_post_does_not_exist(self):
        with self.assertFieldError('id', 'DOES_NOT_EXIST'):
            self.client.call_action('delete_post', id=fuzzy.FuzzyUUID().fuzz())

    def test_delete_post_wrong_organization(self):
        post = factories.PostFactory.create_protobuf()
        with self.assertFieldError('id', 'DOES_NOT_EXIST'):
            self.client.call_action('delete_post', id=post.id)

    def test_delete_post(self):
        post = factories.PostFactory.create_protobuf(profile=self.profile)
        self.client.call_action('delete_post', id=post.id)
        self.assertFalse(models.Post.objects.filter(pk=post.id).exists())
