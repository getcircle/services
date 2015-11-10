from mock import patch
from protobufs.services.post import containers_pb2 as post_containers
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
        self.assertTrue(post.permissions.can_edit)
        self.assertTrue(post.permissions.can_delete)

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

    def test_update_post_draft_to_listed(self):
        post = factories.PostFactory.create_protobuf(
            profile=self.profile,
            state=post_containers.DRAFT,
        )
        post.state = post_containers.LISTED
        response = self.client.call_action('update_post', post=post)
        post = response.result.post
        self.assertEqual(post.state, post_containers.LISTED)

        post.state = post_containers.DRAFT
        # verify we can't go back to DRAFT from listed
        with self.assertFieldError('post.state'):
            self.client.call_action('update_post', post=post)

    def test_update_post_draft_to_unlisted(self):
        post = factories.PostFactory.create_protobuf(
            profile=self.profile,
            state=post_containers.DRAFT,
        )
        post.state = post_containers.UNLISTED
        response = self.client.call_action('update_post', post=post)
        post = response.result.post
        self.assertEqual(post.state, post_containers.UNLISTED)

        post.state = post_containers.DRAFT
        # verify we can't go back to DRAFT from listed
        with self.assertFieldError('post.state'):
            self.client.call_action('update_post', post=post)

        # verify we can list the post
        post.state = post_containers.LISTED
        response = self.client.call_action('update_post', post=post)
        post = response.result.post
        self.assertEqual(post.state, post_containers.LISTED)

        # verify we can unlist again
        post.state = post_containers.UNLISTED
        response = self.client.call_action('update_post', post=post)
        post = response.result.post
        self.assertEqual(post.state, post_containers.UNLISTED)

    def test_update_post_set_file_ids(self):
        post = factories.PostFactory.create_protobuf(profile=self.profile)
        files = [mocks.mock_file(organization_id=self.organization.id) for _ in range(2)]
        post.file_ids.extend([f.id for f in files])
        self.mock.instance.register_mock_object(
            service='file',
            action='get_files',
            return_object=files,
            return_object_path='files',
            ids=[f.id for f in files],
        )

        response = self.client.call_action('update_post', post=post)
        self.assertEqual(len(response.result.post.file_ids), len(post.file_ids))
        self.assertEqual(len(response.result.post.files), len(post.file_ids))
        attachments = models.Attachment.objects.filter(post_id=post.id)
        self.assertEqual(len(attachments), 2)

    @patch('post.actions.service.control.call_action')
    def test_update_post_remove_file_ids(self, patched):
        post = factories.PostFactory.create(profile=self.profile)
        factories.AttachmentFactory.create_batch(size=2, post=post)
        container = post.to_protobuf()
        removed_file_id = container.file_ids.pop(1)

        response = self.client.call_action('update_post', post=container)
        file_ids = response.result.post.file_ids
        self.assertEqual(len(file_ids), 1)
        self.assertNotIn(removed_file_id, file_ids)

        # verify we deleted the file
        args = patched.call_args_list[1][1]
        self.assertEqual(args['service'], 'file')
        self.assertEqual(args['action'], 'delete')
