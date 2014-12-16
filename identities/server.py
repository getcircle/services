import service.control

from . import actions


class Server(service.control.Server):

    service_name = 'identity'

    actions = {
        'create_identity': actions.CreateIdentity,
        'get_identity': actions.GetIdentity,
    }
