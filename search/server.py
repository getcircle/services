import service.control

from . import actions


class Server(service.control.Server):
    service_name = 'search'

    actions = {
        'search': actions.Search,
    }
