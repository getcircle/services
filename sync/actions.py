from service import (
    actions,
    validators,
)

from services.token import parse_token

from . import models


def valid_sync_id(value):
    return models.SyncRequest.objects.filter(id=value).exists()


class StartSync(actions.Action):

    def run(self, *args, **kwargs):
        token = parse_token(self.token)
        sync_request = models.SyncRequest.objects.create(
            organization_id=token.organization_id,
            source=self.request.source,
        )
        self.response.sync_id = str(sync_request.id)


class SyncPayloads(actions.Action):

    required_fields = ('sync_id',)
    type_validators = {
        'sync_id': [validators.is_uuid4],
    }
    field_validators = {
        'sync_id': {
            valid_sync_id: 'DOES_NOT_EXIST',
        }
    }

    def run(self, *args, **kwargs):
        sync_records = []
        for payload in self.request.payloads:
            sync_record = models.SyncRecord(
                sync_id=self.request.sync_id,
                payload=payload.payload,
                payload_type=payload.payload_type,
            )
            sync_records.append(sync_record)
        models.SyncRecord.objects.bulk_create(sync_records)


class CompleteSync(actions.Action):

    required_fields = ('sync_id',)
    type_validators = {
        'sync_id': [validators.is_uuid4],
    }
    field_validators = {
        'sync_id': {
            valid_sync_id: 'DOES_NOT_EXIST',
        }
    }

    def validate(self, *args, **kwargs):
        super(CompleteSync, self).validate(*args, **kwargs)
        if not self.is_error():
            exists = models.SyncJournal.objects.filter(
                sync_id=self.request.sync_id,
                journal_type=models.SyncJournal.JOURNAL_TYPE_SYNC_COMPLETED,
            ).exists()
            if exists:
                raise self.ActionFieldError('sync_id', 'ALREADY_COMPLETED')

    def run(self, *args, **kwargs):
        models.SyncJournal.objects.create(
            sync_id=self.request.sync_id,
            journal_type=models.SyncJournal.JOURNAL_TYPE_SYNC_COMPLETED,
        )
