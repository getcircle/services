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

    def test_complete_upload_upload_id_required(self):
        with self.assertFieldError('upload_id', 'MISSING'):
            self.client.call_action('complete_upload', upload_key=fuzzy.FuzzyText().fuzz())

    def test_complete_upload_upload_key_required(self):
        with self.assertFieldError('upload_key', 'MISSING'):
            self.client.call_action('complete_upload', upload_id=fuzzy.FuzzyUUID().fuzz())

    @patch.object(actions.CompleteUpload, '_complete_upload')
    def test_complete_upload(self, patched):
        patched.return_value = fuzzy.FuzzyText(prefix='https://').fuzz()
        response = self.client.call_action(
            'complete_upload',
            upload_id=fuzzy.FuzzyUUID().fuzz(),
            upload_key=fuzzy.FuzzyText().fuzz(),
        )
        upload = response.result.file
        self.assertEqual(upload.by_profile_id, self.profile.id)
        self.assertEqual(upload.organization_id, self.organization.id)
        file_model = models.File.objects.get(pk=upload.id)
        self.verify_containers(upload, file_model.to_protobuf())
