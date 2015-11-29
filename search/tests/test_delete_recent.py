import service.control

from ..stores.es import types
from services.test import (
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
        self.token = mocks.mock_token(organization_id=self.organization.id)
        self.client = service.control.Client('search', token=self.token)
        self.mock.instance.dont_mock_service('search')

    def test_delete_recent(self):
        recent = factories.RecentFactory.create(profile=self.profile)
        self.client.call_action('delete_recent', id=str(recent.id))
        self.assertFalse(models.Recent.objects.filter(pk=recent.id).exists())
