import json

from django.core.urlresolvers import reverse
import mock
from rest_framework import status
import service.control

from api.test import APITestCase
from services.test import (
    fuzzy,
    mocks,
)


class TestSyncAPI(APITestCase):

    def setUp(self):
        self.start_sync_url = reverse('public-api-v1-sync-start')
        self.sync_users_url = reverse('public-api-v1-sync-users')
        self.sync_groups_url = reverse('public-api-v1-sync-groups')
        self.complete_sync_url = reverse('public-api-v1-sync-complete')
        self.organization = mocks.mock_organization()
        self.token = fuzzy.FuzzyUUID().fuzz()

    def test_start_sync_unauthenticated(self):
        response = self.client.post(self.start_sync_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_start_sync(self):
        self.client.force_authenticate(user=self.organization, token=self.token)
        response = self.client.post(self.start_sync_url)
        self.assertTrue(response.json['sync_id'])

    def test_start_sync_raises_action_error(self):
        side_effect = service.control.CallActionError(mock.MagicMock())
        with mock.patch('api.v1.sync.views.service.control.Client') as mock_client:
            mock_client().call_action.side_effect = side_effect
            self.client.force_authenticate(user=self.organization, token=self.token)
            response = self.client.post(self.start_sync_url)

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

    def test_sync_users_unauthenticated(self):
        response = self.client.post(self.sync_users_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_sync_users(self):
        self.client.force_authenticate(user=self.organization, token=self.token)

        response = self.client.post(self.start_sync_url)
        data = {
            'sync_id': response.json['sync_id'],
            'users': [{'some': 'user', 'payload': 'here'}, {'some': 'user', 'payload': 'here'}],
        }
        response = self.client.post(
            self.sync_users_url,
            data=data,
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_sync_groups_unauthenticated(self):
        response = self.client.post(self.sync_groups_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_sync_groups(self):
        self.client.force_authenticate(user=self.organization, token=self.token)

        response = self.client.post(self.start_sync_url)
        data = {
            'sync_id': response.json['sync_id'],
            'groups': [{'some': 'group', 'payload': 'here'}, {'some': 'group', 'payload': 'here'}],
        }
        response = self.client.post(
            self.sync_groups_url,
            data=data,
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_complete_sync_unauthenticated(self):
        response = self.client.post(self.complete_sync_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_complete_sync(self):
        self.client.force_authenticate(user=self.organization, token=self.token)
        response = self.client.post(self.start_sync_url)
        response = self.client.post(
            self.complete_sync_url,
            data={'sync_id': response.json['sync_id']},
            format='json',
        )
