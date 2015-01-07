import service.control

from . import actions


class Server(service.control.Server):
    service_name = 'user'

    auth_exempt_actions = (
        'authenticate_user',
    )

    actions = {
        'create_user': actions.CreateUser,
        'get_user': actions.GetUser,
        'valid_user': actions.ValidUser,
        'authenticate_user': actions.AuthenticateUser,
    }
