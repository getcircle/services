import service.control

from . import actions
from .actions import update_entities


class Server(service.control.Server):
    service_name = 'search'

    actions = {
        'search': actions.Search,
        'search_v2': actions.SearchV2,
        'update_entities': update_entities.Action,
    }
