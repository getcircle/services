from service.handlers.django_handler import Handler

from credentials import actions as credential_actions
from identities import actions as identity_actions
from users import actions as user_actions


class UserService(Handler):

    actions = {

        # credential actions
        'create_credentials': credential_actions.CreateCredentials,
        'verify_credentials': credential_actions.VerifyCredentials,
        'update_credentials': credential_actions.UpdateCredentials,

        # identity actions
        'create_identity': identity_actions.CreateIdentity,
        'get_identity': identity_actions.GetIdentity,

        # user actions
        'create_user': user_actions.CreateUser,
        'valid_user': user_actions.ValidUser,

    }
