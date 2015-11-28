from service import (
    actions,
    validators,
)
from services.mixins import PreRunParseTokenMixin
from .. import models


class Action(PreRunParseTokenMixin, actions.Action):

    type_validators = {
        'id': [validators.is_uuid4],
    }
    required_fields = ('id',)

    def run(self, *args, **kwargs):
        try:
            r = models.Recent.objects.get(
                organization_id=self.parsed_token.organization_id,
                pk=self.request.id,
            )
        except models.Recent.DoesNotExist:
            raise self.ActionFieldError('id', 'DOES_NOT_EXIST')
        else:
            r.delete()
