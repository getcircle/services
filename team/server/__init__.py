import service.control

from . import actions


class Server(service.control.Server):
    service_name = 'team'

    actions = {
        'create_team': actions.CreateTeam,
        'add_members': actions.AddMembers,
        'get_team': actions.GetTeam,
        'get_members': actions.GetMembers,
        'update_members': actions.UpdateMembers,
        'remove_members': actions.RemoveMembers,
        'join_team': actions.JoinTeam,
        'leave_team': actions.LeaveTeam,
    }
