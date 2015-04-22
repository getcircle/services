import datetime

from protobufs.services.sync.containers import (
    payload_pb2,
    source_pb2,
)
from services.test import factory

from . import models


class SyncRequestFactory(factory.Factory):
    class Meta:
        model = models.SyncRequest

    organization_id = factory.FuzzyUUID()
    source = factory.FuzzyChoice(source_pb2.SourceV1.values())


class SyncRecordFactory(factory.Factory):
    class Meta:
        model = models.SyncRecord

    sync = factory.SubFactory(SyncRequestFactory)
    payload = factory.FuzzyText()
    payload_type = factory.FuzzyChoice(payload_pb2.PayloadV1.PayloadTypeV1.values())


class SyncJournalFactory(factory.Factory):
    class Meta:
        model = models.SyncJournal

    sync = factory.SubFactory(SyncRequestFactory)
    journal_type = models.SyncJournal.JOURNAL_TYPE_SYNC_COMPLETED
