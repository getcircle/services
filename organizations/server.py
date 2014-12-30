import service.control

from . import actions


class Server(service.control.Server):
    service_name = 'organization'

    actions = {
        'create_organization': actions.CreateOrganization,
        'create_team': actions.CreateTeam,
        'get_team': actions.GetTeam,
        'create_address': actions.CreateAddress,
        'delete_address': actions.DeleteAddress,
        'get_address': actions.GetAddress,
        'get_organization': actions.GetOrganization,
    }
