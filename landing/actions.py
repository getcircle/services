from service import (
    actions,
    validators,
)
import service.control


class GetCategories(actions.Action):

    type_validators = {
        'profile_id': [validators.is_uuid4],
    }

    def __init__(self, *args, **kwargs):
        super(GetCategories, self).__init__(*args, **kwargs)
        self.profile_client = service.control.Client('profile', token=self.token)

    def _get_peers_category(self):
        response = self.profile_client.call_action('get_peers', profile_id=self.request.profile_id)
        if not response.success:
            # XXX handle errors properly
            raise Exception('failed to fetch peers')

        peers = self.response.profile_categories.add()
        peers.title = 'Peers'
        peers.content_key = 'title'
        for profile in response.result.profiles:
            container = peers.content.add()
            container.CopyFrom(profile)

    def run(self, *args, **kwargs):
        self._get_peers_category()
