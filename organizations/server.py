import service.control

from . import actions


class Server(service.control.Server):
    service_name = 'organization'

    actions = {
        'create_organization': actions.CreateOrganization,
        'create_team': actions.CreateTeam,
        'get_team': actions.GetTeam,
        'get_teams': actions.GetTeams,
        'get_team_descendants': actions.GetTeamDescendants,
        'create_address': actions.CreateAddress,
        'delete_address': actions.DeleteAddress,
        'get_address': actions.GetAddress,
        'get_addresses': actions.GetAddresses,
        'get_organization': actions.GetOrganization,
        'get_top_level_team': actions.GetTopLevelTeam,
        'create_location': actions.CreateLocation,
        'update_location': actions.UpdateLocation,
        'get_location': actions.GetLocation,
        'get_locations': actions.GetLocations,
    }
