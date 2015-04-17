from protobufs.services.note.containers import note_pb2
from services.test import factory

from . import models


class NoteFactory(factory.Factory):
    class Meta:
        model = models.Note
        protobuf = note_pb2.NoteV1

    for_profile_id = factory.FuzzyUUID()
    owner_profile_id = factory.FuzzyUUID()
    content = factory.FuzzyText()
