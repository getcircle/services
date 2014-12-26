import service.control

from . import actions


class Server(service.control.Server):
    service_name = 'organization'

    actions = {
        'create_organization': actions.CreateOrganization,
        'create_team': actions.CreateTeam,
        'create_address': actions.CreateAddress,
        'delete_address': actions.DeleteAddress,
    }
