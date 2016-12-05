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

    def test_get_file_id_required(self):
        with self.assertFieldError('id', 'MISSING'):
            self.client.call_action('get_file')

    def test_get_file_id_invalid(self):
        with self.assertFieldError('id'):
            self.client.call_action('get_file', id='invalid')

    def test_get_file_wrong_organization(self):
        f = factories.FileFactory.create()
        with self.assertFieldError('id', 'DOES_NOT_EXIST'):
            self.client.call_action('get_file', id=str(f.id))
