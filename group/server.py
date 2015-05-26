import service.control

from . import actions


class Server(service.control.Server):
    service_name = 'group'

    actions = {
        'list_groups': actions.ListGroups,
        'join_group': actions.JoinGroup,
        'respond_to_membership_request': actions.RespondToMembershipRequest,
        'leave_group': actions.LeaveGroup,
        'list_members': actions.ListMembers,
        'get_group': actions.GetGroup,
        'add_to_group': actions.AddToGroup,
        'get_membership_requests': actions.GetMembershipRequests,
    }
