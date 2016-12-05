import service.control

from services.test import (
    mocks,
    MockedTestCase,
)

from .. import factories


class TestGetFiles(MockedTestCase):

    def setUp(self):
        super(TestGetFiles, self).setUp()
        self.organization = mocks.mock_organization()
        self.profile = mocks.mock_profile()
        token = mocks.mock_token(
            organization_id=self.organization.id,
            profile_id=self.profile.id,
        )
        self.client = service.control.Client('file', token=token)
        self.mock.instance.dont_mock_service('file')

    def test_get_files_is_required(self):
        with self.assertFieldError('ids', 'MISSING'):
            self.client.call_action('get_files')

    def test_get_files(self):
        files = factories.FileFactory.create_batch(size=2, organization_id=self.organization.id)
        other_files = factories.FileFactory.create_batch(size=2)
        file_ids = [f.id for f in files] + [f.id for f in other_files]
        response = self.client.call_action('get_files', ids=map(str, file_ids))
        self.assertEqual(len(response.result.files), len(files))
        response_ids = [f.id for f in response.result.files]
        for f in other_files:
            self.assertNotIn(str(f.id), response_ids)

        for f in files:
            self.assertIn(str(f.id), response_ids)

    def test_get_files_invalid_ids(self):
        with self.assertFieldError('ids'):
            self.client.call_action('get_files', ids=['invalid', 'invalid'])
