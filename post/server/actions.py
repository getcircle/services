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

from .. import models
from ..actions import (
    add_to_collection,
    collection_exists,
    create_collection,
    delete_collection,
    get_collection,
    get_collection_permissions,
    get_collection_items,
    get_collections,
    get_collection_id_to_items_dict,
    get_total_items_for_collections,
    inflate_items_source,
    remove_from_collection,
    reorder_collection,
    update_collection,
)
from ..mixins import PostPermissionsMixin
from ..editors import trix


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
            token=self.token,
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
            ids=[str(attachment.file_id)],
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

        trix.delete_post(post.content, self.token)
        post.delete()


class CreateCollection(PreRunParseTokenMixin, actions.Action):

    required_fields = ('collection', 'collection.name')

    def run(self, *args, **kwargs):
        collection = create_collection(
            container=self.request.collection,
            organization_id=self.parsed_token.organization_id,
            by_profile_id=self.parsed_token.profile_id,
            token=self.token,
        )
        collection.to_protobuf(self.response.collection)


class DeleteCollection(PreRunParseTokenMixin, actions.Action):

    required_fields = ('collection_id',)
    type_validators = {
        'collection_id': [validators.is_uuid4],
    }

    def run(self, *args, **kwargs):
        try:
            delete_collection(
                collection_id=self.request.collection_id,
                organization_id=self.parsed_token.organization_id,
                by_profile_id=self.parsed_token.profile_id,
                token=self.token,
            )
        except models.Collection.DoesNotExist:
            raise self.ActionFieldError('collection_id', 'DOES_NOT_EXIST')


class ReorderCollection(PreRunParseTokenMixin, actions.Action):

    required_fields = ('collection_id', 'diffs')
    type_validators = {
        'collection_id': [validators.is_uuid4],
    }

    def run(self, *args, **kwargs):
        try:
            reorder_collection(
                collection_id=self.request.collection_id,
                organization_id=self.parsed_token.organization_id,
                by_profile_id=self.parsed_token.profile_id,
                position_diffs=self.request.diffs,
                token=self.token,
            )
        except models.Collection.DoesNotExist:
            raise self.ActionFieldError('collection_id', 'DOES_NOT_EXIST')


class AddToCollection(PreRunParseTokenMixin, actions.Action):

    required_fields = ('source_id',)
    type_validators = {
        'collection_id': [validators.is_uuid4],
        'owner_id': [validators.is_uuid4],
    }

    def run(self, *args, **kwargs):
        try:
            item = add_to_collection(
                collection_id=self.request.collection_id,
                source=self.request.source,
                source_id=self.request.source_id,
                organization_id=self.parsed_token.organization_id,
                by_profile_id=self.parsed_token.profile_id,
                token=self.token,
                is_default=self.request.is_default,
                owner_type=self.request.owner_type,
                owner_id=self.request.owner_id,
            )
        except models.Collection.DoesNotExist:
            raise self.ActionFieldError('collection_id', 'DOES_NOT_EXIST')

        item.to_protobuf(self.response.item)


class RemoveFromCollection(PreRunParseTokenMixin, actions.Action):

    required_fields = ('collection_id', 'collection_item_id')
    type_validators = {
        'collection_id': [validators.is_uuid4],
        'collection_item_id': [validators.is_uuid4],
    }

    def run(self, *args, **kwargs):
        try:
            remove_from_collection(
                collection_id=self.request.collection_id,
                collection_item_id=self.request.collection_item_id,
                organization_id=self.parsed_token.organization_id,
                by_profile_id=self.parsed_token.profile_id,
                token=self.token,
            )
        except models.Collection.DoesNotExist:
            raise self.ActionFieldError('collection_id', 'DOES_NOT_EXIST')


class UpdateCollection(PreRunParseTokenMixin, actions.Action):

    required_fields = ('collection', 'collection.name')
    type_validators = {
        'collection.id': [validators.is_uuid4],
    }

    def run(self, *args, **kwargs):
        try:
            collection = update_collection(
                container=self.request.collection,
                organization_id=self.parsed_token.organization_id,
                by_profile_id=self.parsed_token.profile_id,
                token=self.token,
            )
        except models.Collection.DoesNotExist:
            raise self.ActionFieldError('collection.id', 'DOES_NOT_EXIST')
        collection.to_protobuf(self.response.collection)


class GetCollections(PreRunParseTokenMixin, actions.Action):

    type_validators = {
        'owner_id': [validators.is_uuid4],
        'ids': [validators.is_uuid4_list],
    }

    def run(self, *args, **kwargs):
        collections = get_collections(
            organization_id=self.parsed_token.organization_id,
            owner_type=self.request.owner_type,
            owner_id=self.request.owner_id,
            source=self.request.source,
            source_id=self.request.source_id,
            is_default=self.request.is_default,
            ids=self.request.ids,
        )
        collections = self.get_paginated_objects(collections)
        collection_ids = [str(c.id) for c in collections]
        item_counts = {}
        if common_utils.should_inflate_field('total_items', self.request.inflations):
            item_counts = get_total_items_for_collections(
                collection_ids=collection_ids,
                organization_id=self.parsed_token.organization_id,
            )

        item_fields = common_utils.fields_for_repeated_items(
            'collections.items',
            self.request.fields,
        )
        item_inflations = common_utils.inflations_for_repeated_items(
            'collections.items',
            self.request.inflations,
        )

        collection_to_items = {}
        if self.request.items_per_collection:
            collection_to_items = get_collection_id_to_items_dict(
                collection_ids=collection_ids,
                number_of_items=self.request.items_per_collection,
                organization_id=self.parsed_token.organization_id,
                fields=item_fields,
                inflations=item_inflations,
            )

        for collection in collections:
            container = self.response.collections.add()
            collection.to_protobuf(
                container,
                inflations=self.request.inflations,
                fields=self.request.fields,
                total_items=item_counts.get(str(collection.id), 0),
            )
            container.items.extend(collection_to_items.get(str(collection.id), []))


class GetCollection(PreRunParseTokenMixin, actions.Action):

    type_validators = {
        'collection_id': [validators.is_uuid4],
        'owner_id': [validators.is_uuid4],
    }

    def _handle_does_not_exist(self):
        if (
            self.request.is_default and
            self.request.owner_id and
            self.request.owner_type
        ):
            # XXX i think this is fine? would there be a case where it mattered
            # that we returned an owner_id etc if you didn't have access to
            # that?
            self.response.collection.is_default = True
            self.response.collection.owner_id = self.request.owner_id
            self.response.collection.owner_type = self.request.owner_type
        else:
            raise self.ActionFieldError('collection_id', 'DOES_NOT_EXIST')

    def run(self, *args, **kwargs):
        try:
            collection = get_collection(
                collection_id=self.request.collection_id,
                organization_id=self.parsed_token.organization_id,
                is_default=self.request.is_default,
                owner_type=self.request.owner_type,
                owner_id=self.request.owner_id,
            )
        except models.Collection.DoesNotExist:
            return self._handle_does_not_exist()

        item_counts = {}
        if common_utils.should_inflate_field('total_items', self.request.inflations):
            item_counts = get_total_items_for_collections(
                collection_ids=[str(collection.id)],
                organization_id=self.parsed_token.organization_id,
            )

        collection.to_protobuf(
            self.response.collection,
            fields=self.request.fields,
            inflations=self.request.inflations,
            total_items=item_counts.get(str(collection.id), 0),
        )

        permissions = get_collection_permissions(
            collection=collection,
            by_profile_id=self.parsed_token.profile_id,
            token=self.token,
        )
        self.response.collection.permissions.CopyFrom(permissions)


class GetCollectionItems(PreRunParseTokenMixin, actions.Action):

    required_fields = ('collection_id',)
    type_validators = {
        'collection_id': [validators.is_uuid4],
    }

    def run(self, *args, **kwargs):
        if not collection_exists(
            collection_id=self.request.collection_id,
            organization_id=self.parsed_token.organization_id,
        ):
            raise self.ActionFieldError('collection_id', 'DOES_NOT_EXIST')

        items = get_collection_items(
            collection_id=self.request.collection_id,
            organization_id=self.parsed_token.organization_id,
        )
        items = self.get_paginated_objects(items)
        containers = inflate_items_source(
            items=items,
            organization_id=self.parsed_token.organization_id,
            inflations=self.request.inflations,
            fields=self.request.fields,
        )
        self.response.items.extend(containers)
