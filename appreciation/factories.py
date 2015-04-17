from protobufs.services.appreciation.containers import appreciation_pb2
from services.test import factory

from . import models


class AppreciationFactory(factory.Factory):
    class Meta:
        model = models.Appreciation
        protobuf = appreciation_pb2.AppreciationV1

    destination_profile_id = factory.FuzzyUUID()
    source_profile_id = factory.FuzzyUUID()
    content = factory.FuzzyText()
