import service.control

from . import actions


class Server(service.control.Server):
    service_name = 'appreciation'

    actions = {
        'create_appreciation': actions.CreateAppreciation,
        'get_appreciation': actions.GetAppreciation,
        'delete_appreciation': actions.DeleteAppreciation,
        'update_appreciation': actions.UpdateAppreciation,
    }
