from mock import patch
import service.control

from services.test import (
    mocks,
    MockedTestCase,
)

from ..models import File


class Test(MockedTestCase):

    def setUp(self):
        super(Test, self).setUp()
        self.organization = mocks.mock_organization()
        self.profile = mocks.mock_profile(organization_id=self.organization.id)
        token = mocks.mock_token(
            organization_id=self.organization.id,
            profile_id=self.profile.id,
        )
        self.client = service.control.Client('file', token=token)
        self.mock.instance.dont_mock_service('file')

    def _mock_boto(self, patched_boto, http_status_code=200, http_response=None):
        patched_boto.client().put_object.side_effect = lambda *args, **kwargs: http_response or {
            'ResponseMetadata': {'HTTPStatusCode': http_status_code}
        }
        patched_boto.client().generate_presigned_url.side_effect = lambda *args, **kwargs: (
            'https://somebucket.amazonaws.com?siginfo'
        )

    def test_upload_file_required(self):
        with self.assertFieldError('file', 'MISSING'):
            self.client.call_action('upload')

    def test_upload_file_name_required(self):
        with self.assertFieldError('file.name', 'MISSING'):
            self.client.call_action('upload', file={'bytes': b'some bytes'})

    def test_upload_file_bytes_required(self):
        with self.assertFieldError('file.bytes', 'MISSING'):
            self.client.call_action('upload', file={'name': 'some file name'})

    @patch('file.actions.boto3')
    def test_upload_file_no_content_type(self, patched_boto):
        self._mock_boto(patched_boto)
        response = self.client.call_action(
            'upload',
            file={'name': 'some_file.keynote', 'bytes': b'some bytes'},
        )
        self.assertEqual(response.result.file.name, 'some_file.keynote')
        self.assertTrue(response.result.file.source_url.startswith('https://somebucket'))
        self.assertTrue(response.result.file.source_url.endswith('.com'))

        instance = File.objects.get(pk=response.result.file.id)
        self.assertEqual(instance.name, response.result.file.name)

    @patch('file.actions.boto3')
    def test_upload_file_non_200_response(self, patched_boto):
        self._mock_boto(patched_boto, http_status_code=400)
        with self.assertRaisesCallActionError() as expected:
            self.client.call_action(
                'upload',
                file={'name': 'some_file.keynote', 'bytes': b'some bytes'},
            )
        self.assertIn('UPLOAD_ERROR', expected.exception.response.errors)

    @patch('file.actions.boto3')
    def test_upload_file_unknown_response(self, patched_boto):
        self._mock_boto(patched_boto, http_response={'unknown': 'response'})
        with self.assertRaisesCallActionError() as expected:
            self.client.call_action(
                'upload',
                file={'name': 'some_file.keynote', 'bytes': b'some bytes'},
            )
        self.assertIn('UPLOAD_ERROR', expected.exception.response.errors)
