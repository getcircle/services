import service.control

from . import actions


class Server(service.control.Server):
    service_name = 'user'

    auth_exempt_actions = (
        'authenticate_user',
    )

    actions = {
        'create_user': actions.CreateUser,
        'update_user': actions.UpdateUser,
        'get_user': actions.GetUser,
        'valid_user': actions.ValidUser,
        'authenticate_user': actions.AuthenticateUser,
        'send_verification_code': actions.SendVerificationCode,
        'verify_verification_code': actions.VerifyVerificationCode,
    }
