from services.test import factory
from protobufs.services.glossary import containers_pb2 as glossary_containers

from . import models


class TermFactory(factory.Factory):
    class Meta:
        model = models.Term
        protobuf = glossary_containers.TermV1

    name = factory.FuzzyText()
    definition = factory.FuzzyText()
    organization_id = factory.FuzzyUUID()
    created_by_profile_id = factory.FuzzyUUID()
