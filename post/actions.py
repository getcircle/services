from common import utils as common_utils
from protobuf_to_dict import protobuf_to_dict
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
        for file_id in self.request.post.file_ids:
            models.Attachment.objects.create(
                post=post,
                organization_id=self.parsed_token.organization_id,
                file_id=file_id,
            )
        post.to_protobuf(
            self.response.post,
            file_ids=self.request.post.file_ids,
            inflations={'exclude': ['html_document']},
        )


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

    def _delete_attachment(self, attachment):
        service.control.call_action(
            service='file',
            action='delete',
            client_kwargs={'token': self.token},
            id=str(attachment.file_id),
        )
        attachment.delete()

    def run(self, *args, **kwargs):

        try:
            post = models.Post.objects.get(
                pk=self.request.post.id,
                organization_id=self.parsed_token.organization_id,
            )
        except models.Post.DoesNotExist:
            raise self.ActionFieldError('post.id', 'DOES_NOT_EXIST')

        if (
            post.state != post_containers.DRAFT
            and self.request.post.state == post_containers.DRAFT
        ):
            raise self.ActionFieldError('post.state', 'INVALID')

        permissions = self.get_permissions(post)
        if not permissions.can_edit:
            raise self.PermissionDenied()

        attachments = post.attachments.filter(
            organization_id=self.parsed_token.organization_id,
        )
        file_ids = []
        for attachment in attachments:
            if str(attachment.file_id) not in self.request.post.file_ids:
                self._delete_attachment(attachment)
            else:
                file_ids.append(str(attachment.file_id))

        for file_id in self.request.post.file_ids:
            if file_id not in file_ids:
                models.Attachment.objects.create(
                    post=post,
                    organization_id=self.parsed_token.organization_id,
                    file_id=file_id,
                )
                file_ids.append(file_id)

        post.update_from_protobuf(
            self.request.post,
            organization_id=self.parsed_token.organization_id,
        )
        post.save()
        post.to_protobuf(
            self.response.post,
            file_ids=file_ids,
            token=self.token,
            inflations={'exclude': ['html_document']},
        )
        self.response.post.permissions.CopyFrom(self.get_permissions(post))


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

        unlisted = post.state in [post_containers.UNLISTED, post_containers.DRAFT]
        is_author = utils.matching_uuids(post.by_profile_id, self.parsed_token.profile_id)
        if unlisted and not is_author:
            raise self.PermissionDenied()

        post.to_protobuf(
            self.response.post,
            inflations=self.request.inflations,
            token=self.token,
            fields=self.request.fields
        )
        self.response.post.permissions.CopyFrom(self.get_permissions(post))


class GetPosts(PreRunParseTokenMixin, actions.Action):

    def is_author(self):
        return self.request.by_profile_id and utils.matching_uuids(
            self.parsed_token.profile_id,
            self.request.by_profile_id,
        )

    def pre_run(self, *args, **kwargs):
        super(GetPosts, self).pre_run(*args, **kwargs)
        if (
            self.request.by_profile_id and
            not self.is_author() and
            not self.request.all_states and
            self.request.state in [post_containers.UNLISTED, post_containers.DRAFT]
        ):
            raise self.PermissionDenied()

    def run(self, *args, **kwargs):
        parameters = {'organization_id': self.parsed_token.organization_id}
        if self.request.ids:
            parameters['id__in'] = self.request.ids
        elif self.request.by_profile_id:
            parameters['by_profile_id'] = self.request.by_profile_id

        if not self.is_author() and self.request.all_states:
            parameters['state'] = post_containers.LISTED
        elif not self.request.all_states:
            parameters['state'] = self.request.state

        posts = models.Post.objects.filter(**parameters).order_by('-changed')
        authors = {}
        if common_utils.should_inflate_field('by_profile', self.request.inflations):
            author_ids = [str(post.by_profile_id) for post in posts]
            profiles = service.control.get_object(
                'profile',
                client_kwargs={'token': self.token},
                action='get_profiles',
                return_object='profiles',
                ids=author_ids
            )
            # XXX redundant protobuf_to_dict call
            authors = dict((profile.id, protobuf_to_dict(profile)) for profile in profiles)
        self.paginated_response(
            self.response.posts,
            posts,
            lambda item, container: item.to_protobuf(
                container.add(),
                inflations=self.request.inflations,
                token=self.token,
                fields=self.request.fields,
                by_profile=authors.get(str(item.by_profile_id), {})
            ),
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
