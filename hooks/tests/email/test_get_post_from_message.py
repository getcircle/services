from botocore.exceptions import ClientError
import mock

from protobufs.services.post import containers_pb2 as post_containers
from services.test import (
    mocks,
    MockedTestCase,
)

from hooks.email import actions
from .helpers import return_fixture


class Test(MockedTestCase):

    def setUp(self):
        super(Test, self).setUp()
        self.organization = mocks.mock_organization()
        self.profile = mocks.mock_profile()
        self.token = mocks.mock_token(
            profile_id=self.profile.id,
            organization_id=self.organization.id,
        )

    @mock.patch('hooks.email.actions.boto3')
    def test_get_post_from_message_does_not_exist(self, patched_boto):
        patched_boto.client().get_object.side_effect = ClientError(mock.MagicMock(), 'mock')
        post = actions.get_post_from_message('invalid', self.token)
        self.assertIsNone(post)

    @mock.patch('hooks.email.actions.boto3')
    def test_get_post_from_message(self, patched_boto):
        return_fixture('simple_email.txt', patched_boto)
        post = actions.get_post_from_message('some id', self.token)
        self.assertIsNotNone(post)
        self.assertEqual(post.title, 'test')
        self.assertEqual(post.content, '<div>test</div>')
        self.assertEqual(post.source, post_containers.EMAIL)
        self.assertEqual(post.source_id, 'some id')

    @mock.patch('hooks.email.actions.boto3')
    def test_get_post_from_message_multipart(self, patched_boto):
        # i'm cheating here since the same file will be returned for each upload call
        self.mock.instance.register_mock_object(
            service='file',
            action='upload',
            return_object=mocks.mock_file(),
            return_object_path='file',
            mock_regex_lookup='file:upload.*',
        )

        return_fixture('multipart_email.txt', patched_boto)
        post = actions.get_post_from_message('some id', self.token)
        self.assertEqual(post.content.count('data-trix-attachment'), 2)

    @mock.patch('hooks.email.actions.boto3')
    def test_get_post_from_message_multipart_inline_attachments(self, patched_boto):
        # i'm cheating here since the same file will be returned for each upload call
        self.mock.instance.register_mock_object(
            service='file',
            action='upload',
            return_object=mocks.mock_file(),
            return_object_path='file',
            mock_regex_lookup='file:upload.*',
        )

        return_fixture('multipart_email_inline_attachments.txt', patched_boto)
        post = actions.get_post_from_message('some id', self.token)
        self.assertEqual(post.content.count('data-trix-attachment'), 4)

    @mock.patch('hooks.email.actions.boto3')
    def test_get_post_from_message_multipart_attachments(self, patched_boto):
        # i'm cheating here since the same file will be returned for each upload call
        self.mock.instance.register_mock_object(
            service='file',
            action='upload',
            return_object=mocks.mock_file(),
            return_object_path='file',
            mock_regex_lookup='file:upload.*',
        )

        return_fixture('multipart_email_attachments.txt', patched_boto)
        post = actions.get_post_from_message('some id', self.token)
        self.assertEqual(post.content.count('data-trix-attachment'), 5)
        self.assertNotIn('<div><br></div>', post.content)
        # NOTE: allow attributes in the opening div
        self.assertEqual(post.content.count('<div'), 1)
        self.assertEqual(post.content.count('</div>'), 1)

    @mock.patch('hooks.email.actions.boto3')
    def test_get_post_from_message_invalid_elements(self, patched_boto):
        # i'm cheating here since the same file will be returned for each upload call
        self.mock.instance.register_mock_object(
            service='file',
            action='upload',
            return_object=mocks.mock_file(),
            return_object_path='file',
            mock_regex_lookup='file:upload.*',
        )

        return_fixture('email_with_invalid_elements.txt', patched_boto)
        post = actions.get_post_from_message('some id', self.token)
        self.assertNotIn('<td', post.content)

    @mock.patch('hooks.email.actions.boto3')
    def test_get_post_from_message_forwarded_email(self, patched_boto):
        return_fixture('forwarded_email.txt', patched_boto)
        post = actions.get_post_from_message('some id', self.token)
        self.assertIn('From: Michael Hahn', post.content)
        self.assertIn('exciting', post.content)
        self.assertIn('you posted', post.content)
