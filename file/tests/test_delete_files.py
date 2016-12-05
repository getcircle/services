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

    def test_delete_file_ids_required(self):
        with self.assertFieldError('ids', 'MISSING'):
            self.client.call_action('delete')

    def test_delete_file(self):
        f = factories.FileFactory.create(organization_id=self.organization.id)
        self.client.call_action('delete', ids=[str(f.id)])
        self.assertFalse(models.File.objects.filter(pk=f.id).exists())

    def test_delete_multiple_files(self):
        files = factories.FileFactory.create_batch(size=4, organization_id=self.organization.id)
        self.client.call_action('delete', ids=[str(f.id) for f in files])
        self.assertFalse(models.File.objects.filter(pk__in=[f.id for f in files]).exists())

    def test_delete_file_does_not_exist(self):
        with self.assertFieldError('ids', 'DO_NOT_EXIST'):
            self.client.call_action('delete', ids=[fuzzy.FuzzyUUID().fuzz()])

    def test_delete_file_invalid_id(self):
        with self.assertFieldError('ids'):
            self.client.call_action('delete', ids=['invalid'])

    def test_delete_file_wrong_organization(self):
        f = factories.FileFactory.create()
        with self.assertFieldError('ids', 'DO_NOT_EXIST'):
            self.client.call_action('delete', ids=[str(f.id)])
