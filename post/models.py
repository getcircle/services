from common import utils
from common.db import models
from protobufs.services.post import containers_pb2 as post_containers
from protobuf_to_dict import protobuf_to_dict
import service.control

from services.utils import should_inflate_field


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
        protobuf = post_containers.PostV1

    def _get_by_profile(self, token):
        return service.control.get_object(
            service='profile',
            action='get_profile',
            client_kwargs={'token': token},
            return_object='profile',
            profile_id=str(self.by_profile_id),
            inflations={'only': ['display_title']},
        )

    def _inflate(self, protobuf, inflations, overrides, token):
        if 'by_profile' not in overrides:
            if should_inflate_field('by_profile', inflations) and token:
                overrides['by_profile'] = protobuf_to_dict(self._get_by_profile(token))
        return overrides

    def to_protobuf(
            self,
            protobuf=None,
            strict=False,
            extra=None,
            inflations=None,
            only=None,
            token=None,
            **overrides
        ):
        protobuf = self.new_protobuf_container(protobuf)
        self._inflate(protobuf, inflations, overrides, token)
        return super(Post, self).to_protobuf(
            protobuf,
            strict=strict,
            extra=extra,
            only=only,
            **overrides
        )
