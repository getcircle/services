from service import (
    actions,
    validators,
)

from services.token import parse_token
from services.utils import matching_uuids

from . import models


def valid_content(content):
    try:
        return len(content) > 0
    except TypeError:
        return False


def valid_note(value):
    return models.Note.objects.filter(pk=value).exists()


class CreateNote(actions.Action):

    type_validators = {
        'note.for_profile_id': [validators.is_uuid4],
        'note.owner_profile_id': [validators.is_uuid4],
    }

    field_validators = {
        'note.content': {
            valid_content: 'MISSING',
        },
    }

    def run(self, *args, **kwargs):
        note = models.Note.objects.from_protobuf(self.request.note)
        note.to_protobuf(self.response.note)


class GetNotes(actions.Action):

    # XXX add some concept of required
    # XXX we probably shouldn't let the user specify "owner_profile_id" and we
    # should fetch it off of the token
    type_validators = {
        'for_profile_id': [validators.is_uuid4],
        'owner_profile_id': [validators.is_uuid4],
    }

    def run(self, *args, **kwargs):
        parameters = {'status__isnull': True}
        if self.request.owner_profile_id:
            parameters['owner_profile_id'] = self.request.owner_profile_id
        if self.request.for_profile_id:
            parameters['for_profile_id'] = self.request.for_profile_id

        notes = models.Note.objects.filter(**parameters).order_by('-changed')
        for note in notes:
            container = self.response.notes.add()
            note.to_protobuf(container)


class DeleteNote(actions.Action):

    field_validators = {
        'note.id': {
            valid_note: 'DOES_NOT_EXIST',
        },
    }

    def validate(self, *args, **kwargs):
        super(DeleteNote, self).validate(*args, **kwargs)
        if not self.is_error():
            token = parse_token(self.token)
            if not matching_uuids(token.profile_id, self.request.note.owner_profile_id):
                self.note_error(
                    'FORBIDDEN',
                    ('FORBIDDEN', 'you do not have permission for this action'),
                )
                self.note_field_error('note.owner_profile_id', 'FORBIDDEN')

    def run(self, *args, **kwargs):
        models.Note.objects.filter(pk=self.request.note.id).update(
            status=models.Note.DELETED_STATUS,
        )


class UpdateNote(DeleteNote):

    def run(self, *args, **kwargs):
        note = models.Note.objects.get(pk=self.request.note.id)
        note.update_from_protobuf(self.request.note)
        note.save()
        note.to_protobuf(self.response.note)
