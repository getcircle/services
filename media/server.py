import service.control

from . import actions


class Server(service.control.Server):
    service_name = 'media'

    actions = {
        'start_image_upload': actions.StartImageUpload,
        'complete_image_upload': actions.CompleteImageUpload,
    }
