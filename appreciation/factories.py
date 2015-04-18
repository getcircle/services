from protobufs.services.appreciation import containers_pb2 as appreciation_containers
from services.test import factory

from . import models


class AppreciationFactory(factory.Factory):
    class Meta:
        model = models.Appreciation
        protobuf = appreciation_containers.AppreciationV1

    destination_profile_id = factory.FuzzyUUID()
    source_profile_id = factory.FuzzyUUID()
    content = factory.FuzzyText()
