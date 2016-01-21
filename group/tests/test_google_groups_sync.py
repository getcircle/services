from mock import MagicMock
import uuid
import unittest

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


@unittest.skip('skip')
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
            token=token,
            requester_profile=self.profile,
            integration=MagicMock(),
        )

    def test_sync_generates_new_uuid(self):
        self.sync_id = uuid.uuid4()
        self.assertNotEqual(
            Sync(self.provider, self.organization).sync_id,
            Sync(self.provider, self.organization).sync_id,
        )
