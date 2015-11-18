from django.conf import settings
import service.control

from services.token import parse_token

from . import actions
from .actions import (
    search_v2,
    update_entities,
    delete_entities,
)


class Server(service.control.Server):
    service_name = 'search'

    actions = {
        'search': actions.Search,
        'search_v2': search_v2.Action,
        'update_entities': update_entities.Action,
        'delete_entities': delete_entities.Action,
    }

    def get_action_class(self, control, action):
        parsed_token = parse_token(control.token)
        SEARCH_V2_ENABLED = settings.SEARCH_V2_ENABLED
        if not SEARCH_V2_ENABLED:
            SEARCH_V2_ENABLED = parsed_token.organization_id in (
                settings.SEARCH_SERVICE_SEARCH_V2_ENABLED_ORGANIZATION_IDS
            )

        if action == 'search_v2' and not SEARCH_V2_ENABLED:
            action = 'search'
        return super(Server, self).get_action_class(control, action)
