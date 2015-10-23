from protobufs.services.post import containers_pb2 as post_containers
import service.control
from service import (
    actions,
    validators,
)

from services.mixins import PreRunParseTokenMixin
from services.utils import should_inflate_field

from . import models


class CreatePost(PreRunParseTokenMixin, actions.Action):

    required_fields = (
        'post',
        'post.title',
        'post.content',
    )

    def run(self, *args, **kwargs):
        post = models.Post.objects.from_protobuf(
            self.request.post,
            organization_id=self.parsed_token.organization_id,
            by_profile_id=self.parsed_token.profile_id,
        )
        post.to_protobuf(self.response.post)


class UpdatePost(PreRunParseTokenMixin, actions.Action):

    required_fields = (
        'post',
        'post.id',
        'post.title',
        'post.content',
    )

    type_validators = {
        'post.id': [validators.is_uuid4],
    }

    def run(self, *args, **kwargs):
        try:
            post = models.Post.objects.get(
                pk=self.request.post.id,
                organization_id=self.parsed_token.organization_id,
                by_profile_id=self.parsed_token.profile_id,
            )
        except models.Post.DoesNotExist:
            raise self.ActionFieldError('post.id', 'DOES_NOT_EXIST')

        post.update_from_protobuf(
            self.request.post,
            organization_id=self.parsed_token.organization_id,
            by_profile_id=self.parsed_token.profile_id,
        )
        post.save()
        post.to_protobuf(self.response.post)


class GetPost(actions.Action):

    def run(self, *args, **kwargs):
        pass


class GetPosts(actions.Action):

    def run(self, *args, **kwargs):
        pass


class DeletePost(actions.Action):

    def run(self, *args, **kwargs):
        pass
