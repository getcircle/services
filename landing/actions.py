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

        if not len(response.result.profiles):
            return

        peers = self.response.profile_categories.add()
        peers.title = 'Peers'
        peers.content_key = 'title'
        for profile in response.result.profiles:
            container = peers.content.add()
            container.CopyFrom(profile)

    def _get_direct_reports_category(self):
        response = self.profile_client.call_action(
            'get_direct_reports',
            profile_id=self.request.profile_id,
        )
        if not response.success:
            # XXX handle errors better
            raise Exception('failed to fetch direct reports')

        if not len(response.result.profiles):
            return

        reports = self.response.profile_categories.add()
        reports.title = 'Direct Reports'
        reports.content_key = 'title'
        for profile in response.result.profiles:
            container = reports.content.add()
            container.CopyFrom(profile)

    def run(self, *args, **kwargs):
        self._get_peers_category()
        self._get_direct_reports_category()
