import service.control

from . import actions


class Server(service.control.Server):
    service_name = 'group'

    actions = {
        'get_groups': actions.GetGroups,
        'join_group': actions.JoinGroup,
        'respond_to_membership_request': actions.RespondToMembershipRequest,
        'leave_group': actions.LeaveGroup,
        'get_members': actions.GetMembers,
        'get_group': actions.GetGroup,
        'add_to_group': actions.AddToGroup,
        'get_membership_requests': actions.GetMembershipRequests,
    }
