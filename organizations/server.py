import service.control

from . import actions


class Server(service.control.Server):
    service_name = 'organization'

    actions = {
        'add_team_member': actions.AddTeamMember,
        'create_organization': actions.CreateOrganization,
        'create_team': actions.CreateTeam,
        'get_team_members': actions.GetTeamMembers,
        'remove_team_member': actions.RemoveTeamMember,
        'add_team_members': actions.AddTeamMembers,
        'remove_team_members': actions.RemoveTeamMembers,
    }
