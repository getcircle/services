from protobufs.services.file import containers_pb2 as file_containers

from services.test import factory

from . import models


class FileFactory(factory.Factory):
    class Meta:
        model = models.File
        protobuf = file_containers.FileV1

    by_profile_id = factory.FuzzyUUID()
    organization_id = factory.FuzzyUUID()
    name = factory.FuzzyText()
    size = factory.FuzzyInteger(1000, 10000)
    key = factory.FuzzyText()
