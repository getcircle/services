import service.control

from . import actions


class Server(service.control.Server):
    service_name = 'landing'

    actions = {
        'get_categories': actions.GetCategories,
    }
