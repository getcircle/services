from common.db import models
from protobufs.services.file import containers_pb2 as file_containers


class File(models.UUIDModel, models.TimestampableModel):

    by_profile_id = models.UUIDField()
    organization_id = models.UUIDField(db_index=True)
    source_url = models.CharField(max_length=255)

    class Meta:
        protobuf = file_containers.FileV1
