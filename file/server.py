import service.control

from . import actions


class Server(service.control.Server):
    service_name = 'file'

    actions = {
        'start_upload': actions.StartUpload,
        'complete_upload': actions.CompleteUpload,
        'get_files': actions.GetFiles,
    }
