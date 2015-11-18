"""Create an index for the token's organization.

This will only create an index if one doesn't exist already.

"""
from service import actions

from services.mixins import PreRunParseTokenMixin

from ..stores.es.indices.organization.actions import (
    create_index,
    DuplicateIndex,
)


class Action(PreRunParseTokenMixin, actions.Action):

    def run(self, *args, **kwargs):
        try:
            create_index(self.parsed_token.organization_id)
        except DuplicateIndex:
            raise self.ActionFieldError('token.organization_id', 'DUPLICATE')
