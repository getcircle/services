from protobufs.note_service_pb2 import NoteService
from services.test import factory

from . import models


class NoteFactory(factory.Factory):
    class Meta:
        model = models.Note
        protobuf = NoteService.Containers.Note

    for_profile_id = factory.FuzzyUUID()
    owner_profile_id = factory.FuzzyUUID()
    content = factory.FuzzyText()
