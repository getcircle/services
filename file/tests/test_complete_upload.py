from mock import patch
import service.control

from services.test import (
    fuzzy,
    mocks,
    MockedTestCase,
)

from .. import (
    actions,
    models,
)


class MockFile(object):

    def __init__(self, content_type='image/png', size=2323):
        self.content_type = content_type
        self.size = size


class TestCompleteUpload(MockedTestCase):

    def setUp(self):
        super(TestCompleteUpload, self).setUp()
        self.organization = mocks.mock_organization()
        self.profile = mocks.mock_profile()
        self.token = mocks.mock_token(
            organization_id=self.organization.id,
            profile_id=self.profile.id,
        )
        self.client = service.control.Client('file', token=self.token)
        self.mock.instance.dont_mock_service('file')

    def test_complete_upload_upload_id_required(self):
        with self.assertFieldError('upload_id', 'MISSING'):
            self.client.call_action(
                'complete_upload',
                upload_key=fuzzy.FuzzyText().fuzz(),
                file_name=fuzzy.FuzzyText().fuzz(),
            )

    def test_complete_upload_upload_key_required(self):
        with self.assertFieldError('upload_key', 'MISSING'):
            self.client.call_action(
                'complete_upload',
                upload_id=fuzzy.FuzzyUUID().fuzz(),
                file_name=fuzzy.FuzzyText().fuzz(),
            )

    def test_complete_upload_file_name_required(self):
        with self.assertFieldError('file_name', 'MISSING'):
            self.client.call_action(
                'complete_upload',
                upload_key=fuzzy.FuzzyText().fuzz(),
                upload_id=fuzzy.FuzzyUUID().fuzz(),
            )

    @patch.object(actions.CompleteUpload, '_complete_upload')
    def test_complete_upload(self, patched):
        patched.return_value = fuzzy.FuzzyText(prefix='https://').fuzz(), MockFile('text/plain'), 'us-east-1'
        response = self.client.call_action(
            'complete_upload',
            upload_id=fuzzy.FuzzyUUID().fuzz(),
            upload_key=fuzzy.FuzzyText().fuzz(),
            file_name='some file.txt',
            content_type='text/plain',
        )
        upload = response.result.file
        self.assertEqual(upload.by_profile_id, self.profile.id)
        self.assertEqual(upload.organization_id, self.organization.id)
        self.assertEqual(upload.name, 'some file.txt')
        self.assertEqual(upload.content_type, 'text/plain')
        file_model = models.File.objects.get(pk=upload.id)
        self.verify_containers(upload, file_model.to_protobuf(token=self.token))

    @patch.object(actions.CompleteUpload, '_complete_upload')
    def test_complete_upload_content_type_not_required(self, patched):
        patched.return_value = fuzzy.FuzzyText(prefix='https://').fuzz(), MockFile('text/plain'), 'us-east-1'
        response = self.client.call_action(
            'complete_upload',
            upload_id=fuzzy.FuzzyUUID().fuzz(),
            upload_key=fuzzy.FuzzyText().fuzz(),
            file_name='some file.txt',
        )
        upload = response.result.file
        self.assertEqual(upload.by_profile_id, self.profile.id)
        self.assertEqual(upload.organization_id, self.organization.id)
        self.assertEqual(upload.name, 'some file.txt')
        file_model = models.File.objects.get(pk=upload.id)
        self.verify_containers(upload, file_model.to_protobuf(token=self.token))
