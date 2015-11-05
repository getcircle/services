from protobufs.services.post import containers_pb2 as post_containers
from service import (
    actions,
    validators,
)
import service.control

from services.mixins import PreRunParseTokenMixin
from services import utils

from . import models
from .mixins import PostPermissionsMixin


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


class UpdatePost(PostPermissionsMixin, actions.Action):

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

        if post.state != post_containers.DRAFT and self.request.post.state == post_containers.DRAFT:
            raise self.ActionFieldError('post.state', 'INVALID')

        post.update_from_protobuf(
            self.request.post,
            organization_id=self.parsed_token.organization_id,
            by_profile_id=self.parsed_token.profile_id,
        )
        post.save()
        post.to_protobuf(self.response.post)
        self.response.post.permissions.CopyFrom(permissions)


class GetPost(PostPermissionsMixin, actions.Action):

    required_fields = ('id',)
    type_validators = {
        'id': [validators.is_uuid4],
    }

    def run(self, *args, **kwargs):
        try:
            post = models.Post.objects.get(
                pk=self.request.id,
                organization_id=self.parsed_token.organization_id,
            )
        except models.Post.DoesNotExist:
            raise self.ActionFieldError('id', 'DOES_NOT_EXIST')
        post.to_protobuf(self.response.post, inflations=self.request.inflations, token=self.token)
        self.response.post.permissions.CopyFrom(self.get_permissions(post))


class GetPosts(PreRunParseTokenMixin, actions.Action):

    def run(self, *args, **kwargs):
        parameters = {'organization_id': self.parsed_token.organization_id}
        if self.request.ids:
            parameters['id__in'] = self.request.ids
        elif self.request.by_profile_id:
            parameters['by_profile_id'] = self.request.by_profile_id

        if not self.request.all_states:
            parameters['state'] = self.request.state

        posts = models.Post.objects.filter(**parameters).order_by('-changed')
        self.paginated_response(
            self.response.posts,
            posts,
            lambda item, container: item.to_protobuf(container.add()),
        )


class DeletePost(PostPermissionsMixin, actions.Action):

    required_fields = ('id',)
    type_validators = {
        'id': [validators.is_uuid4],
    }

    def run(self, *args, **kwargs):
        try:
            post = models.Post.objects.get(
                organization_id=self.parsed_token.organization_id,
                pk=self.request.id,
            )
        except models.Post.DoesNotExist:
            raise self.ActionFieldError('id', 'DOES_NOT_EXIST')

        permissions = self.get_permissions(post)
        if not permissions.can_delete:
            raise self.PermissionDenied()

        post.delete()
