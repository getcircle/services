import service.control

from . import actions


class Server(service.control.Server):
    service_name = 'file'

    actions = {
        'delete': actions.Delete,
        'complete_upload': actions.CompleteUpload,
        'get_files': actions.GetFiles,
        'start_upload': actions.StartUpload,
        'upload': actions.Upload,
        # TODO remove unused
        'get_file': actions.GetFile,
    }
