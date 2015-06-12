from mock import MagicMock
import uuid

from services.test import (
    fuzzy,
    mocks,
    TestCase,
)

from .. import models
from ..factories import provider as provider_factories
from ..factories import models as model_factories
from ..providers.google import Provider
from ..providers.google.sync import Sync


class TestGoogleGroupsCache(TestCase):

    def setUp(self):
        self.organization = mocks.mock_organization(domain='circlehq.co')
        self.profile = mocks.mock_profile(
            email='michael@circlehq.co',
            organization_id=self.organization.id,
        )
        token = mocks.mock_token(
            organization_id=self.organization.id,
            profile_id=self.profile.id,
        )
        self.provider = Provider(
            self.profile,
            organization=self.organization,
            token=token,
            integration=MagicMock(),
        )

    def test_sync_generates_new_uuid(self):
        self.sync_id = uuid.uuid4()
        self.assertNotEqual(Sync(self.provider).sync_id, Sync(self.provider).sync_id)
