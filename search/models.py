from common.db import models
from protobufs.services.search import containers_pb2 as search_containers


class Recent(models.UUIDModel, models.TimestampableModel):

    by_profile_id = models.UUIDField()
    organization_id = models.UUIDField()
    document_type = models.CharField(max_length=255)
    document_id = models.UUIDField()

    class Meta:
        index_together = ('organization_id', 'by_profile_id')
