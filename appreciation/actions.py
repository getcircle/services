from service import (
    actions,
    validators,
)

from services.token import parse_token
from services.utils import matching_uuids

from . import models


def valid_appreciation(value):
    return models.Appreciation.objects.filter(pk=value).exists()


class CreateAppreciation(actions.Action):

    type_validators = {
        'appreciation.destination_profile_id': [validators.is_uuid4],
        'appreciation.source_profile_id': [validators.is_uuid4],
    }

    def run(self, *args, **kwargs):
        appreciation = models.Appreciation.objects.from_protobuf(self.request.appreciation)
        appreciation.to_protobuf(self.response.appreciation)


class GetAppreciation(actions.Action):

    type_validators = {
        'destination_profile_id': [validators.is_uuid4],
    }

    def run(self, *args, **kwargs):
        appreciation = models.Appreciation.objects.filter(
            destination_profile_id=self.request.destination_profile_id,
        ).order_by('-changed')
        self.paginated_response(
            self.response.appreciation,
            appreciation,
            lambda item, container: item.to_protobuf(container.add()),
        )


class DeleteAppreciation(actions.Action):

    field_validators = {
        'appreciation.id': {
            valid_appreciation: 'DOES_NOT_EXIST',
        },
    }

    def validate(self, *args, **kwargs):
        super(DeleteAppreciation, self).validate(*args, **kwargs)
        if not self.is_error():
            token = parse_token(self.token)
            appreciation = self.request.appreciation
            if (
                not matching_uuids(token.profile_id, appreciation.destination_profile_id) and
                not matching_uuids(token.profile_id, appreciation.source_profile_id)
            ):
                raise self.ActionError(
                    'FORBIDDEN',
                    ('FORBIDDEN', 'you do not have permission for this action'),
                )

    def run(self, *args, **kwargs):
        models.Appreciation.objects.filter(pk=self.request.appreciation.id).update(
            status=models.Appreciation.DELETED_STATUS,
        )


class UpdateAppreciation(actions.Action):

    field_validators = {
        'appreciation.id': {
            valid_appreciation: 'DOES_NOT_EXIST',
        },
    }

    def validate(self, *args, **kwargs):
        super(UpdateAppreciation, self).validate(*args, **kwargs)
        if not self.is_error():
            token = parse_token(self.token)
            if not matching_uuids(token.profile_id, self.request.appreciation.source_profile_id):
                # TODO make this like self.ForbiddenError
                raise self.ActionError(
                    'FORBIDDEN',
                    ('FORBIDDEN', 'you do not have permision for this action'),
                )

    def run(self, *args, **kwargs):
        # XXX this should be simplified
        appreciation = models.Appreciation.objects.get(pk=self.request.appreciation.id)
        appreciation.update_from_protobuf(self.request.appreciation)
        appreciation.save()
        appreciation.to_protobuf(self.response.appreciation)
