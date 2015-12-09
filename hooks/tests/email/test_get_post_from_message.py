from botocore.exceptions import ClientError
import mock

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
        self.assertEqual(post.content, 'test\n')

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
        self.assertEqual(len(post.file_ids), 2)

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
        self.assertEqual(len(post.file_ids), 4)
