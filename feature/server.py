import service.control

from . import actions


class Server(service.control.Server):
    service_name = 'feature'

    actions = {
        'get_flags': actions.GetFlags,
    }
