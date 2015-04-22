import service.control

from . import actions


class Server(service.control.Server):
    service_name = 'sync'

    actions = {
        'start_sync': actions.StartSync,
        'sync_payloads': actions.SyncPayloads,
        'complete_sync': actions.CompleteSync,
    }
