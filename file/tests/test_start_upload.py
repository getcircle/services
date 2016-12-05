# coding=utf-8

from mock import patch
import service.control

from services.test import (
    fuzzy,
    mocks,
    MockedTestCase,
)


class TestStartUpload(MockedTestCase):

    def setUp(self):
        super(TestStartUpload, self).setUp()
        self.organization = mocks.mock_organization()
        self.profile = mocks.mock_profile()
        token = mocks.mock_token(
            organization_id=self.organization.id,
            profile_id=self.profile.id,
        )
        self.client = service.control.Client('file', token=token)
        self.mock.instance.dont_mock_service('file')

    def test_start_upload_file_name_required(self):
        with self.assertFieldError('file_name', 'MISSING'):
            self.client.call_action('start_upload', content_type='text/plain')

    @patch('file.actions.utils.S3Manager')
    def test_start_upload(self, patched):
        bucket = patched().get_bucket()
        type(bucket.initiate_multipart_upload()).id = fuzzy.FuzzyUUID().fuzz()
        bucket.get_location.return_value = 'us-west-2'

        response = self.client.call_action(
            'start_upload',
            file_name='some report.pdf',
            content_type='text/plain',
        )
        instructions = response.result.upload_instructions
        self.assertTrue(instructions.upload_id)
        self.assertTrue(instructions.upload_url)
        self.assertTrue(instructions.upload_key)

    @patch('file.actions.utils.S3Manager')
    def test_start_upload_content_type_not_required(self, patched):
        bucket = patched().get_bucket()
        type(bucket.initiate_multipart_upload()).id = fuzzy.FuzzyUUID().fuzz()
        bucket.get_location.return_value = 'us-west-2'

        response = self.client.call_action(
            'start_upload',
            file_name='some report.pdf',
        )
        instructions = response.result.upload_instructions
        self.assertTrue(instructions.upload_id)
        self.assertTrue(instructions.upload_url)
        self.assertTrue(instructions.upload_key)

    @patch('file.actions.utils.S3Manager')
    def test_start_upload_unicode_characters_file_name(self, patched):
        file_name = 'test_ 某物.png'
        bucket = patched().get_bucket()
        type(bucket.initiate_multipart_upload()).id = fuzzy.FuzzyUUID().fuzz()
        bucket.get_location.return_value = 'us-west-2'

        response = self.client.call_action('start_upload', file_name=file_name)
        instructions = response.result.upload_instructions
        self.assertTrue(instructions.upload_key)

        file_name = 'Inbox_–_mwhahn_gmail_com.png'
        response = self.client.call_action('start_upload', file_name=file_name)
        instructions = response.result.upload_instructions
        self.assertTrue(instructions.upload_key)
