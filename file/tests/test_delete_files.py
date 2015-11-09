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


class TestDeleteFiles(MockedTestCase):

    def setUp(self):
        super(TestDeleteFiles, self).setUp()
        self.organization = mocks.mock_organization()
        self.profile = mocks.mock_profile()
        token = mocks.mock_token(
            organization_id=self.organization.id,
            profile_id=self.profile.id,
        )
        self.client = service.control.Client('file', token=token)
        self.mock.instance.dont_mock_service('file')

    def test_delete_file_id_required(self):
        with self.assertFieldError('id', 'MISSING'):
            self.client.call_action('delete')

    def test_delete_file(self):
        f = factories.FileFactory.create(organization_id=self.organization.id)
        self.client.call_action('delete', id=str(f.id))
        self.assertFalse(models.File.objects.filter(pk=f.id).exists())

    def test_delete_file_does_not_exist(self):
        with self.assertFieldError('id', 'DOES_NOT_EXIST'):
            self.client.call_action('delete', id=fuzzy.FuzzyUUID().fuzz())

    def test_delete_file_invalid_id(self):
        with self.assertFieldError('id'):
            self.client.call_action('delete', id='invalid')

    def test_delete_file_wrong_organization(self):
        f = factories.FileFactory.create()
        with self.assertFieldError('id', 'DOES_NOT_EXIST'):
            self.client.call_action('delete', id=str(f.id))
