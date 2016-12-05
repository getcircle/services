import service.control

from ..stores.es import types
from services.test import (
    fuzzy,
    mocks,
    MockedTestCase,
)
from .. import (
    factories,
    models
)


class Test(MockedTestCase):

    def setUp(self, *args, **kwargs):
        super(Test, self).setUp(*args, **kwargs)
        self.organization = mocks.mock_organization()
        self.profile = mocks.mock_profile(organization_id=self.organization.id)
        self.token = mocks.mock_token(organization_id=self.organization.id, profile_id=self.profile.id)
        self.client = service.control.Client('search', token=self.token)
        self.mock.instance.dont_mock_service('search')

    def test_delete_recent(self):
        recent = factories.RecentFactory.create(profile=self.profile)
        self.client.call_action('delete_recent', id=str(recent.id))
        self.assertFalse(models.Recent.objects.filter(pk=recent.id).exists())

    def test_delete_recent_id_required(self):
        with self.assertFieldError('id', 'MISSING'):
            self.client.call_action('delete_recent')

    def test_delete_recent_does_not_exist(self):
        with self.assertFieldError('id', 'DOES_NOT_EXIST'):
            self.client.call_action('delete_recent', id=fuzzy.FuzzyUUID().fuzz())

    def test_delete_recent_not_creator(self):
        otherProfile = mocks.mock_profile(organization_id=self.organization.id)
        recent = factories.RecentFactory.create(profile=otherProfile)
        with self.assertFieldError('id', 'DOES_NOT_EXIST'):
            self.client.call_action('delete_recent', id=str(recent.id))
