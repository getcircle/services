from common.db import models
from django.conf import settings
from protobufs.services.file import containers_pb2 as file_containers


def _safe_int(value):
    if value is not None:
        return int(value)


class File(models.UUIDModel, models.TimestampableModel):

    as_dict_value_transforms = {'size': _safe_int}

    by_profile_id = models.UUIDField()
    organization_id = models.UUIDField()
    source_url = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=255)
    size = models.BigIntegerField(null=True)
    bucket = models.CharField(max_length=64, default=settings.AWS_S3_FILE_BUCKET)
    key = models.CharField(max_length=255)

    class Meta:
        protobuf = file_containers.FileV1
        index_together = ('id', 'organization_id')
