import service.control

from . import actions


class Server(service.control.Server):
    service_name = 'note'

    actions = {
        'create_note': actions.CreateNote,
        'get_notes': actions.GetNotes,
    }
