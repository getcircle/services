from protobufs.appreciation_service_pb2 import AppreciationService
from services.test import factory

from . import models


class AppreciationFactory(factory.Factory):
    class Meta:
        model = models.Appreciation
        protobuf = AppreciationService.Containers.Appreciation

    destination_profile_id = factory.FuzzyUUID()
    source_profile_id = factory.FuzzyUUID()
    content = factory.FuzzyText()
