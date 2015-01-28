from service import (
    actions,
    validators,
)

from . import models


def valid_content(content):
    try:
        return len(content) > 0
    except TypeError:
        return False


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

    type_validators = {
        'for_profile_id': [validators.is_uuid4],
        'owner_profile_id': [validators.is_uuid4],
    }

    def run(self, *args, **kwargs):
        notes = models.Note.objects.filter(
            owner_profile_id=self.request.owner_profile_id,
            for_profile_id=self.request.for_profile_id,
        ).order_by('-changed')
        for note in notes:
            container = self.response.notes.add()
            note.to_protobuf(container)
