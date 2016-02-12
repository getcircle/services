from cacheops import cached_as
from common import utils
from common.db import models
from protobufs.services.post import containers_pb2 as post_containers
from protobuf_to_dict import protobuf_to_dict
import service.control

from search.stores.es.types.post.utils import transform_html

from .template import (
    TEMPLATE,
    TEMPLATE_STYLE,
)
from .utils import clean


class Post(models.UUIDModel, models.TimestampableModel):

    as_dict_value_transforms = {
        'state': int,
        'source': int,
    }
    from_protobuf_transforms = {
        'content': clean,
    }

    protobuf_include_fields = ('snippet',)

    title = models.CharField(max_length=255)
    content = models.TextField()
    organization_id = models.UUIDField()
    by_profile_id = models.UUIDField()
    state = models.SmallIntegerField(
        choices=utils.model_choices_from_protobuf_enum(post_containers.PostStateV1),
        default=post_containers.DRAFT,
    )
    source = models.SmallIntegerField(
        choices=utils.model_choices_from_protobuf_enum(post_containers.PostSourceV1),
        default=post_containers.WEB,
    )
    source_id = models.CharField(max_length=255, null=True)

    class Meta:
        index_together = (('organization_id', 'by_profile_id'), ('organization_id', 'state'))
        protobuf = post_containers.PostV1

    @property
    def snippet(self):

        @cached_as(self)
        def _get_snippet():
            return transform_html(self.content)[:80]

        return _get_snippet()

    @property
    def html_document(self):
        return TEMPLATE.format(
            title=self.title,
            content=self.content,
            style=TEMPLATE_STYLE,
        )

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

        if (
            'html_document' not in overrides
            and utils.should_inflate_field('html_document', inflations)
        ):
            overrides['html_document'] = self.html_document

        return overrides

    def to_protobuf(self, protobuf=None, inflations=None, token=None, fields=None, **overrides):
        protobuf = self.new_protobuf_container(protobuf)
        self._inflate(protobuf, inflations, overrides, token)
        return super(Post, self).to_protobuf(
            protobuf,
            inflations=inflations,
            fields=fields,
            **overrides
        )


class Attachment(models.UUIDModel, models.TimestampableModel):

    post = models.ForeignKey(Post, related_name='attachments')
    organization_id = models.UUIDField()
    file_id = models.UUIDField()


class Collection(models.UUIDModel, models.TimestampableModel):

    as_dict_value_transforms = {
        'owner_type': int,
    }

    organization_id = models.UUIDField(editable=False)
    owner_id = models.UUIDField()
    owner_type = models.SmallIntegerField(
        choices=utils.model_choices_from_protobuf_enum(post_containers.CollectionV1.OwnerTypeV1),
        default=post_containers.CollectionV1.PROFILE,
    )
    name = models.CharField(max_length=64)
    # is_default is a NullBooleanField to enforce only 1 default collection per
    # owner_type and owner_id
    is_default = models.NullBooleanField(editable=False, null=True)
    by_profile_id = models.UUIDField(null=True, editable=False)

    class Meta:
        index_together = ('id', 'organization_id')
        unique_together = ('organization_id', 'owner_id', 'owner_type', 'is_default')
        protobuf = post_containers.CollectionV1


class CollectionItem(models.UUIDModel, models.TimestampableModel):

    as_dict_value_transforms = {
        'source': int,
        'position': int,
    }

    collection = models.ForeignKey(Collection)
    position = models.PositiveSmallIntegerField()
    by_profile_id = models.UUIDField(null=True)
    organization_id = models.UUIDField()
    source = models.SmallIntegerField(
        choices=utils.model_choices_from_protobuf_enum(post_containers.CollectionItemV1.SourceV1),
        default=post_containers.CollectionItemV1.LUNO,
    )
    source_id = models.CharField(max_length=128)

    class Meta:
        index_together = (
            ('organization_id', 'source', 'source_id'),
        )
        # This index is created with custom sql:
        # post/migrations/0009_auto_20160212_2047.py to support initially
        # deferring the constraint check. this allows us to reorder the
        # collection in a single transaction.
        unique_together = ('organization_id', 'collection', 'position')
        protobuf = post_containers.CollectionItemV1
