import service.control

from . import actions


class Server(service.control.Server):

    service_name = 'credential'

    actions = {
        'create_credentials': actions.CreateCredentials,
        'verify_credentials': actions.VerifyCredentials,
        'update_credentials': actions.UpdateCredentials,
    }
