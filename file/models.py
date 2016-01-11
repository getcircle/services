from common.db import models
from protobufs.services.file import containers_pb2 as file_containers


def _safe_int(value):
    if value is not None:
        return int(value)


class File(models.UUIDModel, models.TimestampableModel):

    as_dict_value_transforms = {'size': _safe_int}

    by_profile_id = models.UUIDField()
    organization_id = models.UUIDField(db_index=True)
    source_url = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=255)
    size = models.BigIntegerField(null=True)

    class Meta:
        protobuf = file_containers.FileV1
