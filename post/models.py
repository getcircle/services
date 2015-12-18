from common import utils
from common.db import models
from protobufs.services.post import containers_pb2 as post_containers
from protobuf_to_dict import protobuf_to_dict
import service.control


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
        index_together = (('organization_id', 'by_profile_id'), ('organization_id', 'state'))
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

    def _should_fetch_attachments(self, overrides, inflations):
        # ensure that we have created the object before fetching attachments.
        # certian test cases can hit this when we use the `build` method of the
        # factory and provide an non-uuid primary key value intentionally
        if (
            ('file_ids' not in overrides and utils.should_inflate_field('file_ids', inflations)) or
            ('files' not in overrides and utils.should_inflate_field('files', inflations))
        ) and self.created:
            return True
        return False

    def _inflate_files(self, attachments, token):
        files = service.control.get_object(
            service='file',
            action='get_files',
            client_kwargs={'token': token},
            return_object='files',
            ids=[str(a.file_id) for a in attachments],
        )
        return [protobuf_to_dict(f) for f in files]

    def _inflate(self, protobuf, inflations, overrides, token):
        if 'by_profile' not in overrides:
            if utils.should_inflate_field('by_profile', inflations) and token:
                overrides['by_profile'] = protobuf_to_dict(self._get_by_profile(token))

        should_fetch_attachments = self._should_fetch_attachments(overrides, inflations)
        if should_fetch_attachments:
            attachments = Attachment.objects.filter(
                post_id=self.pk,
                organization_id=self.organization_id,
            )
            if attachments:
                if (
                    'file_ids' not in overrides and
                    utils.should_inflate_field('file_ids', inflations)
                ):
                    overrides['file_ids'] = map(str, [a.file_id for a in attachments])
                if (
                    'files' not in overrides and
                    utils.should_inflate_field('files', inflations) and
                    token
                ):
                    overrides['files'] = self._inflate_files(attachments, token)

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


class Attachment(models.UUIDModel, models.TimestampableModel):

    post = models.ForeignKey(Post, related_name='attachments')
    organization_id = models.UUIDField()
    file_id = models.UUIDField()
