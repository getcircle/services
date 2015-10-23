from common import utils
from common.db import models
from protobufs.services.post import containers_pb2 as post_containers


class Post(models.UUIDModel, models.TimestampableModel):

    as_dict_value_transforms = {'state': int}

    title = models.CharField(max_length=255)
    content = models.TextField()
    organization_id = models.UUIDField()
    by_profile_id = models.UUIDField()
    state = models.SmallIntegerField(
        choices=utils.model_choices_from_protobuf_enum(post_containers.PostStateV1),
        default=post_containers.DRAFT,
    )

    class Meta:
        index_together = ('organization_id', 'by_profile_id')
