import service.control

from . import actions


class Server(service.control.Server):
    service_name = 'notification'

    actions = {
        'get_preferences': actions.GetPreferences,
        'update_preference': actions.UpdatePreference,
        'register_device': actions.RegisterDevice,
    }
