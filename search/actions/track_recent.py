from service import actions
from services.mixins import PreRunParseTokenMixin
from .. import models


class Action(PreRunParseTokenMixin, actions.Action):

    required_fields = (
        'tracking_details',
        'tracking_details.document_type',
        'tracking_details.document_id',
    )

    def run(self, *args, **kwargs):
        models.Recent.objects.from_protobuf(
            self.request.tracking_details,
            organization_id=self.parsed_token.organization_id,
            by_profile_id=self.parsed_token.profile_id,
        )
