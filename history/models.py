from common.db import models
from common import utils
from protobufs.services.history import containers_pb2 as history_containers


class Action(models.UUIDModel, models.TimestampableModel):

    as_dict_value_transforms = {
        'action_type': int,
        'method_type': int,
    }

    table_name = models.CharField(max_length=64)
    column_name = models.CharField(max_length=64, null=True)
    data_type = models.CharField(max_length=32, null=True)
    old_value = models.TextField(null=True)
    new_value = models.TextField(null=True)
    action_type = models.SmallIntegerField(
        choices=utils.model_choices_from_protobuf_enum(history_containers.ActionTypeV1),
    )
    method_type = models.SmallIntegerField(
        choices=utils.model_choices_from_protobuf_enum(history_containers.MethodTypeV1),
    )
    organization_id = models.UUIDField(db_index=True)
    correlation_id = models.UUIDField()
    by_profile_id = models.UUIDField()
    primary_key_name = models.CharField(max_length=64)
    primary_key_value = models.CharField(max_length=255)

    class Meta:
        protobuf = history_containers.ActionV1
