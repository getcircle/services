from service import (
    actions,
    validators,
)

from services import mixins
from services.token import parse_token

from . import models


class CreateTerm(mixins.PreRunParseTokenMixin, actions.Action):

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
        term.to_protobuf(self.response.term)


class UpdateTerm(mixins.PreRunParseTokenMixin, actions.Action):

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
        term.update_from_protobuf(self.request.term)
        term.save()
        term.to_protobuf(self.response.term)


class GetTerm(actions.Action):

    def pre_run(self, *args, **kwargs):
        self.parsed_token = parse_token(self.token)

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
        term.to_protobuf(self.response.term)


class GetTerms(mixins.PreRunParseTokenMixin, actions.Action):

    type_validators = {
        'ids': [validators.is_uuid4_list],
    }

    def run(self, *args, **kwargs):
        parameters = {'organization_id': self.parsed_token.organization_id}
        if self.request.ids:
            parameters['pk__in'] = self.request.ids

        terms = models.Term.objects.filter(**parameters)
        self.paginated_response(
            self.response.terms,
            terms,
            lambda item, container: item.to_protobuf(container.add()),
        )


class DeleteTerm(mixins.PreRunParseTokenMixin, actions.Action):

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

        term.delete()
