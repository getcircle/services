import service.control

from . import actions


class Server(service.control.Server):
    service_name = 'user'

    actions = {
        'create_user': actions.CreateUser,
        'valid_user': actions.ValidUser,
    }
