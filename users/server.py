import service.control

from . import actions


class Server(service.control.Server):
    service_name = 'user'

    auth_exempt_actions = (
        'authenticate_user',
        'get_authorization_instructions',
        'complete_authorization',
    )

    actions = {
        'create_user': actions.CreateUser,
        'bulk_create_users': actions.BulkCreateUsers,
        'update_user': actions.UpdateUser,
        'get_user': actions.GetUser,
        'valid_user': actions.ValidUser,
        'authenticate_user': actions.AuthenticateUser,
        'send_verification_code': actions.SendVerificationCode,
        'verify_verification_code': actions.VerifyVerificationCode,
        'get_authorization_instructions': actions.GetAuthorizationInstructions,
        'complete_authorization': actions.CompleteAuthorization,
        'get_identities': actions.GetIdentities,
        'record_device': actions.RecordDevice,
        'request_access': actions.RequestAccess,
    }
