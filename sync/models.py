from common.db import models
from common import utils
from protobufs.services.sync.containers import (
    payload_pb2,
    source_pb2,
)


class SyncRequest(models.UUIDModel, models.TimestampableModel):

    organization_id = models.UUIDField(db_index=True)
    source = models.SmallIntegerField(
        choices=utils.model_choices_from_protobuf_enum(source_pb2.SourceV1),
        db_index=True,
    )


class SyncRecord(models.UUIDModel, models.TimestampableModel):

    sync = models.ForeignKey(SyncRequest, db_index=True)
    payload = models.TextField()
    payload_type = models.SmallIntegerField(
        choices=utils.model_choices_from_protobuf_enum(payload_pb2.PayloadV1.PayloadTypeV1),
        db_index=True,
    )


class SyncJournal(models.UUIDModel, models.TimestampableModel):

    JOURNAL_TYPE_SYNC_COMPLETED = 0
    JOURNAL_TYPE_RECORD_PROCESSED = 1
    JOURNAL_TYPES = (
        ('SyncCompleted', JOURNAL_TYPE_SYNC_COMPLETED),
        ('RecordProcessed', JOURNAL_TYPE_RECORD_PROCESSED),
    )

    sync = models.ForeignKey(SyncRequest)
    record = models.ForeignKey(SyncRecord, null=True)
    journal_type = models.SmallIntegerField(choices=JOURNAL_TYPES)

    class Meta:
        unique_together = ('sync', 'journal_type', 'record')
