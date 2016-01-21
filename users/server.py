import service.control

from . import actions


class Server(service.control.Server):
    service_name = 'user'

    auth_exempt_actions = (
        'authenticate_user',
        'complete_authorization',
        'get_authentication_instructions',
        'request_access',
    )

    actions = {
        'create_user': actions.CreateUser,
        'bulk_create_users': actions.BulkCreateUsers,
        'get_user': actions.GetUser,
        'authenticate_user': actions.AuthenticateUser,
        'logout': actions.Logout,
        'get_authorization_instructions': actions.GetAuthorizationInstructions,
        'complete_authorization': actions.CompleteAuthorization,
        'get_identities': actions.GetIdentities,
        'record_device': actions.RecordDevice,
        'request_access': actions.RequestAccess,
        'delete_identity': actions.DeleteIdentity,
        'get_authentication_instructions': actions.GetAuthenticationInstructions,
        'get_active_devices': actions.GetActiveDevices,
    }
