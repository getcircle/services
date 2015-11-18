from service import actions

from services.mixins import PreRunParseTokenMixin
from ..tasks import delete_entities


class Action(PreRunParseTokenMixin, actions.Action):

    required_fields = ('ids',)

    def run(self, *args, **kwargs):
        delete_entities.delay(
            ids=self.request.ids,
            entity_type=self.request.type,
            organization_id=self.parsed_token.organization_id,
        )
