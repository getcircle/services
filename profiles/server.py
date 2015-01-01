import service.control

from . import actions


class Server(service.control.Server):
    service_name = 'profile'

    actions = {
        'create_profile': actions.CreateProfile,
        'update_profile': actions.UpdateProfile,
        'get_profile': actions.GetProfile,
        'get_extended_profile': actions.GetExtendedProfile,
        'create_tags': actions.CreateTags,
        'add_tags': actions.AddTags,
        'get_tags': actions.GetTags,
    }
