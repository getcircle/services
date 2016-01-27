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
        token = mocks.mock_token(organization_id=self.organization.id, profile_id=self.profile.id)
        self.client = service.control.Client('post', token=token)
        self.mock.instance.dont_mock_service('post')

    def test_get_post_id_required(self):
        with self.assertFieldError('id', 'MISSING'):
            self.client.call_action('get_post')

    def test_get_post_invalid_id(self):
        with self.assertFieldError('id'):
            self.client.call_action('get_post', id='invalid')

    def test_get_post_wrong_organization(self):
        post = factories.PostFactory.create_protobuf()
        with self.assertFieldError('id', 'DOES_NOT_EXIST'):
            self.client.call_action('get_post', id=post.id)

    def test_get_post_does_not_exist(self):
        with self.assertFieldError('id', 'DOES_NOT_EXIST'):
            self.client.call_action('get_post', id=fuzzy.FuzzyUUID().fuzz())

    def test_get_post(self):
        self.mock.instance.register_mock_object(
            service='profile',
            action='get_profile',
            return_object=self.profile,
            return_object_path='profile',
            mock_regex_lookup='profile:get_profile:.*',
        )
        expected_post = factories.PostFactory.create_protobuf(profile=self.profile)
        response = self.client.call_action('get_post', id=expected_post.id)
        post = response.result.post
        self.verify_containers(self.profile, post.by_profile)
        self.assertTrue(post.permissions.can_edit)
        self.assertTrue(post.permissions.can_delete)
        self.assertFalse(post.permissions.can_add)

    def test_get_post_not_author(self):
        by_profile = mocks.mock_profile(organization_id=self.organization.id)
        self.mock.instance.register_mock_object(
            service='profile',
            action='get_profile',
            return_object=by_profile,
            return_object_path='profile',
            mock_regex_lookup='profile:get_profile:.*',
        )
        expected_post = factories.PostFactory.create_protobuf(
            profile=by_profile,
            state=post_containers.LISTED,
        )
        response = self.client.call_action('get_post', id=expected_post.id)
        post = response.result.post
        self.verify_containers(by_profile, post.by_profile)
        self.assertFalse(post.permissions.can_edit)
        self.assertFalse(post.permissions.can_delete)
        self.assertFalse(post.permissions.can_add)

    def test_get_post_admin(self):
        by_profile = mocks.mock_profile(organization_id=self.organization.id)
        # register mock object for post.to_protobuf expansion
        self.mock.instance.register_mock_object(
            service='profile',
            action='get_profile',
            return_object=by_profile,
            return_object_path='profile',
            profile_id=by_profile.id,
            inflations={'disabled': False, 'only': ['display_title']},
        )
        # register mock object for permissions
        self.profile.is_admin = True
        self.mock.instance.register_mock_object(
            service='profile',
            action='get_profile',
            return_object=self.profile,
            return_object_path='profile',
        )

        expected_post = factories.PostFactory.create_protobuf(
            profile=by_profile,
            state=post_containers.LISTED,
        )
        response = self.client.call_action('get_post', id=expected_post.id)
        post = response.result.post
        self.verify_containers(by_profile, post.by_profile)
        self.assertTrue(post.permissions.can_edit)
        self.assertTrue(post.permissions.can_delete)

    def test_get_post_unlisted(self):
        by_profile = mocks.mock_profile(organization_id=self.organization.id)
        self.mock.instance.register_mock_object(
            service='profile',
            action='get_profile',
            return_object=by_profile,
            return_object_path='profile',
            mock_regex_lookup='profile:get_profile:.*',
        )
        post = factories.PostFactory.create_protobuf(
            profile=by_profile,
            state=post_containers.UNLISTED,
        )
        with self.assertRaisesCallActionError() as expected:
            self.client.call_action('get_post', id=post.id)

        self.assertIn('PERMISSION_DENIED', expected.exception.response.errors)

    def test_get_post_with_attachments(self):
        post = factories.PostFactory.create(profile=self.profile)
        attachments = factories.AttachmentFactory.create_batch(size=2, post=post)
        mock_files = []
        for attachment in attachments:
            mock_files.append(
                mocks.mock_file(id=attachment.file_id, organization_id=attachment.organization_id)
            )

        self.mock.instance.register_mock_object(
            service='file',
            action='get_files',
            return_object=mock_files,
            return_object_path='files',
            ids=[str(a.file_id) for a in attachments],
        )

        response = self.client.call_action('get_post', id=str(post.id))
        self.assertEqual(len(response.result.post.files), len(attachments))
        for f in response.result.post.files:
            self.assertTrue(f.source_url)

    def test_get_post_inflate_html_document(self):
        post = factories.PostFactory.create(profile=self.profile)
        response = self.client.call_action(
            'get_post',
            id=str(post.id),
            inflations={'only': ['html_document']},
        )
        html_document = response.result.post.html_document
        self.assertTrue(html_document.startswith('<!doctype html>'))
        self.assertIn(post.title, html_document)
        self.assertIn(post.content, html_document)
