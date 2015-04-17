import service.control

from . import actions


class Server(service.control.Server):
    service_name = 'feed'

    actions = {
        'get_profile_feed': actions.GetProfileFeed,
        'get_organization_feed': actions.GetOrganizationFeed,
    }
