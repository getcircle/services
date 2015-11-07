import service.control

from . import actions
from .actions import (
    search_v2,
    update_entities,
)


class Server(service.control.Server):
    service_name = 'search'

    actions = {
        'search': actions.Search,
        'search_v2': search_v2.Action,
        'update_entities': update_entities.Action,
    }
