import service.control

from . import actions


class Server(service.control.Server):
    service_name = 'payment'

    auth_exempt_actions = (
        'store_token',
    )

    actions = {
        'store_token': actions.StoreToken,
    }
