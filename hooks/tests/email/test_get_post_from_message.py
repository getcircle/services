from botocore.exceptions import ClientError
import mock
from services.test import MockedTestCase

from hooks.email import actions
from .helpers import return_fixture


class Test(MockedTestCase):

    @mock.patch('hooks.email.actions.boto3')
    def test_get_post_from_message_does_not_exist(self, patched_boto):
        patched_boto.client().get_object.side_effect = ClientError(mock.MagicMock(), 'mock')
        post = actions.get_post_from_message('invalid')
        self.assertIsNone(post)

    @mock.patch('hooks.email.actions.boto3')
    def test_get_post_from_message(self, patched_boto):
        return_fixture('simple_email.txt', patched_boto)
        post = actions.get_post_from_message('some id')
        self.assertIsNotNone(post)
        self.assertEqual(post.title, 'test')
        self.assertEqual(post.content, 'test\n')
