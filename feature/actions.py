from django.conf import settings
from service import actions
import service.control


POSTS_FEATURE = 'posts'


class GetFlags(actions.Action):

    def run(self, *args, **kwargs):
        organization = service.control.get_object(
            service='organization',
            action='get_organization',
            client_kwargs={'token': self.token},
            return_object='organization',
        )
        if organization.domain in settings.FEATURE_SERVICE_POSTS_ENABLED_ORGANIZATIONS:
            self.response.flags[POSTS_FEATURE] = True
