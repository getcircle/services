import service.control

from . import actions


class Server(service.control.Server):
    service_name = 'history'

    actions = {
        'record_action': actions.RecordAction,
    }
