from common.db import models
from protobufs.services.profile import containers_pb2 as profile_containers
from protobufs.services.glossary import containers_pb2 as glossary_containers


class Term(models.UUIDModel, models.TimestampableModel):

    name = models.CharField(max_length=255)
    definition = models.TextField()
    organization_id = models.UUIDField(db_index=True, editable=False)
    created_by_profile_id = models.UUIDField(editable=False)

    class Meta:
        unique_together = ('name', 'organization_id')
        protobuf = glossary_containers.TermV1
