from protobufs.services.history import containers_pb2 as history_containers
from services.test import factory

from . import models


class ActionFactory(factory.Factory):
    class Meta:
        model = models.Action

    column_name = factory.FuzzyText()
    data_type = factory.FuzzyText()
    old_value = factory.FuzzyText()
    new_value = factory.FuzzyText()
    action_type = factory.FuzzyChoice(history_containers.ActionTypeV1.values())
    method_type = factory.FuzzyChoice(history_containers.MethodTypeV1.values())
    organization_id = factory.FuzzyUUID()
    correlation_id = factory.FuzzyUUID()
    by_profile_id = factory.FuzzyUUID()
