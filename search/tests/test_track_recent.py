import uuid
import service.control

from ..stores.es import types
from services.test import (
    mocks,
    MockedTestCase,
)


class Test(MockedTestCase):

    def setUp(self, *args, **kwargs):
        super(Test, self).setUp(*args, **kwargs)
        self.organization = mocks.mock_organization()
        self.token = mocks.mock_token(organization_id=self.organization.id)
        self.client = service.control.Client('search', token=self.token)
        self.mock.instance.dont_mock_service('search')

    def test_track_recent(self):
        response = self.client.call_action('track_recent', tracking_details={
            'document_id': str(uuid.uuid4()),
            'document_type': types.ProfileV1._doc_type.name,
        })
        self.assertTrue(response.success)
