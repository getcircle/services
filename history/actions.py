import uuid

from service import actions

from services import mixins

from . import models
from protobufs.services.history import containers_pb2 as history_containers


class RecordAction(mixins.PreRunParseTokenMixin, actions.Action):

    required_fields = (
        'action',
        'action.column_name',
        'action.data_type',
        'action.action_type',
        'action.method_type',
    )

    def validate(self, *args, **kwargs):
        super(RecordAction, self).validate(*args, **kwargs)
        if not self.is_error():
            if (
                self.request.action.method_type != history_containers.DELETE
                and not self.request.action.new_value
            ):
                raise self.ActionFieldError('action.new_value', 'MISSING')

    def run(self, *args, **kwargs):
        models.Action.objects.from_protobuf(
            self.request.action,
            organization_id=self.parsed_token.organization_id,
            by_profile_id=self.parsed_token.profile_id,
            # TODO implement correlation_id
            correlation_id=uuid.uuid4(),
        )
