from protobufs.services.common import containers_pb2 as common_containers
from service import (
    actions,
    validators,
)
import service.control

from services import mixins
from services import utils

from . import models


class TermPermissionsMixin(object):

    @property
    def requester_profile(self):
        # TODO it would be great if we could test this was only called once by
        # having a counter in the mock transport
        if not hasattr(self, '_requester_profile'):
            self._requester_profile = service.control.get_object(
                service='profile',
                action='get_profile',
                return_object='profile',
                client_kwargs={'token': self.token},
                profile_id=self.parsed_token.profile_id,
            )
        return self._requester_profile

    def get_permissions(self, term):
        permissions = common_containers.PermissionsV1()
        if utils.matching_uuids(term.created_by_profile_id, self.parsed_token.profile_id):
            permissions.can_edit = True
            permissions.can_add = True
            permissions.can_delete = True
        else:
            if self.requester_profile.is_admin:
                permissions.can_edit = True
                permissions.can_add = True
                permissions.can_delete = True
        return permissions


class CreateTerm(mixins.PreRunParseTokenMixin, TermPermissionsMixin, actions.Action):

    required_fields = (
        'term',
        'term.name',
        'term.definition',
    )

    def run(self, *args, **kwargs):
        term = models.Term.objects.from_protobuf(self.request.term, commit=False)
        # TODO we should be ensured that these fields are populated, will raise
        # an integrity error otherwise
        term.organization_id = self.parsed_token.organization_id
        term.created_by_profile_id = self.parsed_token.profile_id
        term.save()
        self.response.term.permissions.CopyFrom(self.get_permissions(term))
        term.to_protobuf(self.response.term)


class UpdateTerm(mixins.PreRunParseTokenMixin, TermPermissionsMixin, actions.Action):

    required_fields = (
        'term',
        'term.id',
        'term.name',
        'term.definition',
    )

    type_validators = {
        'term.id': [validators.is_uuid4],
    }

    def run(self, *args, **kwargs):
        term = models.Term.objects.get(pk=self.request.term.id)
        permissions = self.get_permissions(term)
        if not permissions.can_edit:
            raise self.PermissionDenied()

        term.update_from_protobuf(self.request.term)
        term.save()
        self.response.term.permissions.CopyFrom(permissions)
        term.to_protobuf(self.response.term)


class GetTerm(mixins.PreRunParseTokenMixin, TermPermissionsMixin, actions.Action):

    def run(self, *args, **kwargs):
        parameters = {'organization_id': self.parsed_token.organization_id}
        if self.request.HasField('id'):
            parameters['id'] = self.request.id
        elif self.request.HasField('name'):
            parameters['name'] = self.request.name

        try:
            term = models.Term.objects.get(**parameters)
        except models.Term.DoesNotExist:
            lookup_key = None
            if self.request.HasField('id'):
                lookup_key = 'id'
            elif self.request.HasField('name'):
                lookup_key = 'name'
            raise self.ActionFieldError(lookup_key, 'DOES_NOT_EXIST')

        self.response.term.permissions.CopyFrom(self.get_permissions(term))
        term.to_protobuf(self.response.term)


class GetTerms(mixins.PreRunParseTokenMixin, TermPermissionsMixin, actions.Action):

    type_validators = {
        'ids': [validators.is_uuid4_list],
    }

    def run(self, *args, **kwargs):
        parameters = {'organization_id': self.parsed_token.organization_id}
        if self.request.ids:
            parameters['pk__in'] = self.request.ids

        def serialize_to_term(item, container):
            item_container = container.add()
            item_container.permissions.CopyFrom(self.get_permissions(item))
            item.to_protobuf(item_container)

        terms = models.Term.objects.filter(**parameters)
        self.paginated_response(
            self.response.terms,
            terms,
            serialize_to_term,
        )


class DeleteTerm(mixins.PreRunParseTokenMixin, TermPermissionsMixin, actions.Action):

    required_fields = ('id',)
    type_validators = {
        'id': [validators.is_uuid4],
    }

    def run(self, *args, **kwargs):
        try:
            term = models.Term.objects.get(
                pk=self.request.id,
                organization_id=self.parsed_token.organization_id,
            )
        except models.Term.DoesNotExist:
            raise self.ActionFieldError('id', 'DOES_NOT_EXIST')

        permissions = self.get_permissions(term)
        if not permissions.can_delete:
            raise self.PermissionDenied()

        term.delete()
