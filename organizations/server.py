import service.control

from . import actions


class Server(service.control.Server):
    service_name = 'organization'

    auth_exempt_actions = (
        'get_sso_metadata',
    )

    actions = {
        'create_organization': actions.CreateOrganization,
        'get_team': actions.GetTeam,
        'update_team': actions.UpdateTeam,
        'get_teams': actions.GetTeams,
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
        'add_direct_reports': actions.AddDirectReports,
        'set_manager': actions.SetManager,
        'get_profile_reporting_details': actions.GetProfileReportingDetails,
        'get_team_reporting_details': actions.GetTeamReportingDetails,
        'get_location_members': actions.GetLocationMembers,
        'add_location_members': actions.AddLocationMembers,
        'get_descendants': actions.GetDescendants,
        'get_sso_metadata': actions.GetSSOMetadata,
    }
