import service.control

from . import actions


class Server(service.control.Server):
    service_name = 'organization'

    actions = {
        'create_organization': actions.CreateOrganization,
        'create_team': actions.CreateTeam,
        'get_team': actions.GetTeam,
        'get_teams': actions.GetTeams,
        'get_team_children': actions.GetTeamChildren,
        'create_address': actions.CreateAddress,
        'delete_address': actions.DeleteAddress,
        'get_address': actions.GetAddress,
        'get_addresses': actions.GetAddresses,
        'get_organization': actions.GetOrganization,
        'get_top_level_team': actions.GetTopLevelTeam,
    }
