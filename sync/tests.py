import json
import service.control

from protobufs.services.sync.containers import source_pb2
from protobufs.services.sync.containers import payload_pb2

from services.test import (
    fuzzy,
    mocks,
    TestCase,
)

from . import (
    factories,
    models,
)


class TestSync(TestCase):

    def setUp(self):
        self.organization_id = fuzzy.FuzzyUUID().fuzz()
        self.client = service.control.Client(
            'sync',
            token=mocks.mock_token(organization_id=self.organization_id),
        )

    def test_start_sync(self):
        response = self.client.call_action('start_sync', source=source_pb2.LDAP)
        self.assertTrue(response.result.sync_id)

        sync_request = models.SyncRequest.objects.get(id=response.result.sync_id)
        self.assertEqual(sync_request.organization_id, sync_request.organization_id)

    def test_sync_payloads_sync_id_required(self):
        with self.assertFieldError('sync_id', 'MISSING'):
            self.client.call_action('sync_payloads')

    def test_sync_payloads_invalid_sync_id(self):
        with self.assertFieldError('sync_id'):
            self.client.call_action('sync_payloads', sync_id='invalid')

    def test_sync_payloads_sync_id_does_not_exist(self):
        with self.assertFieldError('sync_id', 'DOES_NOT_EXIST'):
            self.client.call_action('sync_payloads', sync_id=fuzzy.FuzzyUUID().fuzz())

    def test_sync_payloads_users(self):
        response = self.client.call_action('start_sync', source=source_pb2.LDAP)
        sync_id = response.result.sync_id

        json_payload = json.dumps([
            {'some': 'values', 'related': 'to', 'a': 'user'},
            {'some': 'values', 'related': 'to', 'a': 'user'},
            {'some': 'values', 'related': 'to', 'a': 'user'},
            {'some': 'values', 'related': 'to', 'a': 'user'},
        ])
        payload = payload_pb2.PayloadV1()
        payload.payload = json_payload
        payload.payload_type = payload_pb2.PayloadV1.USERS

        response = self.client.call_action(
            'sync_payloads',
            sync_id=sync_id,
            payloads=[payload],
        )

        sync_record = models.SyncRecord.objects.get(sync_id=sync_id)
        self.assertEqual(sync_record.payload, payload.payload)
        self.assertEqual(sync_record.payload_type, payload.payload_type)

    def test_sync_multiple_payloads_single_call(self):
        response = self.client.call_action('start_sync', source=source_pb2.LDAP)
        sync_id = response.result.sync_id

        payloads = []
        for payload_type in payload_pb2.PayloadV1.PayloadTypeV1.values():
            payload = payload_pb2.PayloadV1()
            payload.payload = json.dumps([{'some': 'payload'}])
            payload.payload_type = payload_type
            payloads.append(payload)

        response = self.client.call_action('sync_payloads', payloads=payloads, sync_id=sync_id)
        self.assertEqual(models.SyncRecord.objects.filter(sync_id=sync_id).count(), len(payloads))

    def test_sync_multiple_payloads_multiple_calls(self):
        response = self.client.call_action('start_sync', source=source_pb2.LDAP)
        sync_id = response.result.sync_id

        payloads = []
        for payload_type in payload_pb2.PayloadV1.PayloadTypeV1.values():
            payload = payload_pb2.PayloadV1()
            payload.payload = json.dumps([{'some': 'payload'}])
            payload.payload_type = payload_type
            payloads.append(payload)

        for payload in payloads:
            self.client.call_action('sync_payloads', payloads=[payload], sync_id=sync_id)
        self.assertEqual(models.SyncRecord.objects.filter(sync_id=sync_id).count(), len(payloads))

    def test_complete_sync_invalid_sync_id(self):
        with self.assertFieldError('sync_id'):
            self.client.call_action('complete_sync', sync_id='invalid')

    def test_complete_sync_sync_id_does_not_exist(self):
        with self.assertFieldError('sync_id', 'DOES_NOT_EXIST'):
            self.client.call_action('complete_sync', sync_id=fuzzy.FuzzyUUID().fuzz())

    def test_complete_sync_sync_id_required(self):
        with self.assertFieldError('sync_id', 'MISSING'):
            self.client.call_action('complete_sync')

    def test_sync_full_life_cycle(self):
        response = self.client.call_action('start_sync', source=source_pb2.LDAP)
        sync_id = response.result.sync_id

        json_payload = json.dumps([
            {'some': 'values', 'related': 'to', 'a': 'user'},
            {'some': 'values', 'related': 'to', 'a': 'user'},
            {'some': 'values', 'related': 'to', 'a': 'user'},
            {'some': 'values', 'related': 'to', 'a': 'user'},
        ])
        payload = payload_pb2.PayloadV1()
        payload.payload = json_payload
        payload.payload_type = payload_pb2.PayloadV1.USERS

        response = self.client.call_action(
            'sync_payloads',
            sync_id=sync_id,
            payloads=[payload],
        )

        sync_record = models.SyncRecord.objects.get(sync_id=sync_id)
        self.assertEqual(sync_record.payload, payload.payload)
        self.assertEqual(sync_record.payload_type, payload.payload_type)

        response = self.client.call_action('complete_sync', sync_id=sync_id)
        sync_journal = models.SyncJournal.objects.get(sync_id=sync_id)
        self.assertIsNone(sync_journal.record_id)
        self.assertEqual(sync_journal.journal_type, models.SyncJournal.JOURNAL_TYPE_SYNC_COMPLETED)

    def test_sync_duplicate_calls_to_complete_sync(self):
        sync_request = factories.SyncRequestFactory.create()
        self.client.call_action('complete_sync', sync_id=str(sync_request.id))
        with self.assertFieldError('sync_id', 'ALREADY_COMPLETED'):
            self.client.call_action('complete_sync', sync_id=str(sync_request.id))
