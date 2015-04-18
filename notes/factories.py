from protobufs.services.note import containers_pb2 as note_containers
from services.test import factory

from . import models


class NoteFactory(factory.Factory):
    class Meta:
        model = models.Note
        protobuf = note_containers.NoteV1

    for_profile_id = factory.FuzzyUUID()
    owner_profile_id = factory.FuzzyUUID()
    content = factory.FuzzyText()
