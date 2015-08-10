import uuid

from service import actions

from services import mixins

from . import models


class RecordAction(mixins.PreRunParseTokenMixin, actions.Action):

    required_fields = (
        'action',
        'action.table_name',
        'action.column_name',
        'action.data_type',
        'action.action_type',
        'action.method_type',
    )

    def run(self, *args, **kwargs):
        models.Action.objects.from_protobuf(
            self.request.action,
            organization_id=self.parsed_token.organization_id,
            by_profile_id=self.parsed_token.profile_id,
            # TODO implement correlation_id
            correlation_id=uuid.uuid4(),
        )
