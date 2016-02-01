import service.control

from . import actions


class Server(service.control.Server):
    service_name = 'team'

    actions = {
        'create_team': actions.CreateTeam,
        'add_members': actions.AddMembers,
        'get_team': actions.GetTeam,
    }
