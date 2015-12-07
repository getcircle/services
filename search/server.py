import service.control

from . import actions
from .actions import (
    create_index,
    delete_entities,
    search_v2,
    update_entities,
    track_recent,
    get_recents,
    delete_recent,
)


class Server(service.control.Server):
    service_name = 'search'

    actions = {
        'create_index': create_index.Action,
        'delete_entities': delete_entities.Action,
        'search': actions.Search,
        'search_v2': search_v2.Action,
        'update_entities': update_entities.Action,
        'track_recent': track_recent.Action,
        'get_recents': get_recents.Action,
        'delete_recent': delete_recent.Action,
    }
