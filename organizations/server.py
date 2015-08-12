import service.control

from . import actions


class Server(service.control.Server):
    service_name = 'organization'

    actions = {
        'create_organization': actions.CreateOrganization,
        'get_team': actions.GetTeam,
        'update_team': actions.UpdateTeam,
        'get_organization': actions.GetOrganization,
        'create_location': actions.CreateLocation,
        'update_location': actions.UpdateLocation,
        'get_location': actions.GetLocation,
        'get_locations': actions.GetLocations,
        'create_token': actions.CreateToken,
        'get_tokens': actions.GetTokens,
        'enable_integration': actions.EnableIntegration,
        'get_integration': actions.GetIntegration,
        'disable_integration': actions.DisableIntegration,
    }
