from protobufs.services.post import containers_pb2 as post_containers
import service.control
from service import (
    actions,
    validators,
)

from services.mixins import PreRunParseTokenMixin
from services import utils

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


class GetPost(PreRunParseTokenMixin, actions.Action):

    required_fields = ('id',)
    type_validators = {
        'id': [validators.is_uuid4],
    }

    def populate_permissions(self, post):
        if utils.matching_uuids(self.parsed_token.profile_id, post.by_profile_id):
            post.permissions.can_edit = True
            post.permissions.can_delete = True

    def run(self, *args, **kwargs):
        try:
            post = models.Post.objects.get(
                pk=self.request.id,
                organization_id=self.parsed_token.organization_id,
            )
        except models.Post.DoesNotExist:
            raise self.ActionFieldError('id', 'DOES_NOT_EXIST')
        post.to_protobuf(self.response.post, inflations=self.request.inflations, token=self.token)
        self.populate_permissions(self.response.post)


class GetPosts(PreRunParseTokenMixin, actions.Action):

    def run(self, *args, **kwargs):
        by_profile_id = self.parsed_token.profile_id
        if self.request.by_profile_id:
            by_profile_id = self.request.by_profile_id

        parameters = {
            'organization_id': self.parsed_token.organization_id,
            'by_profile_id': by_profile_id,
        }
        if not self.request.all_states:
            parameters['state'] = self.request.state

        posts = models.Post.objects.filter(**parameters).order_by('-changed')
        self.paginated_response(
            self.response.posts,
            posts,
            lambda item, container: item.to_protobuf(container.add()),
        )


class DeletePost(actions.Action):

    def run(self, *args, **kwargs):
        pass
