import service.control

from ..stores.es import types
from services.test import (
    fuzzy,
    mocks,
    MockedTestCase,
)
from .. import models


class Test(MockedTestCase):

    def setUp(self, *args, **kwargs):
        super(Test, self).setUp(*args, **kwargs)
        self.organization = mocks.mock_organization()
        self.profile = mocks.mock_profile(organization_id=self.organization.id)
        self.token = mocks.mock_token(organization_id=self.organization.id, profile_id=self.profile.id)
        self.client = service.control.Client('search', token=self.token)
        self.mock.instance.dont_mock_service('search')

    def test_track_recent(self):
        document_id = fuzzy.uuid()
        response = self.client.call_action('track_recent', tracking_details={
            'document_id': document_id,
            'document_type': types.ProfileV1._doc_type.name,
        })
        self.assertTrue(response.success)
        self.assertTrue(models.Recent.objects.filter(by_profile_id=self.profile.id, organization_id=self.organization.id, document_id=document_id).exists())

    def test_track_recent_tracking_details_required(self):
        with self.assertFieldError('tracking_details', 'MISSING'):
            self.client.call_action('track_recent')

    def test_track_recent_document_type_required(self):
        with self.assertFieldError('tracking_details.document_type', 'MISSING'):
            self.client.call_action('track_recent', tracking_details={
                'document_id': fuzzy.uuid(),
            })

    def test_track_recent_document_id_required(self):
        with self.assertFieldError('tracking_details.document_id', 'MISSING'):
            self.client.call_action('track_recent', tracking_details={
                'document_type': types.ProfileV1._doc_type.name,
            })
