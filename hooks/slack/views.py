import arrow
import logging
from protobufs.services.organization.containers import integration_pb2
from rest_framework import (
    exceptions,
    viewsets,
)
from rest_framework.renderers import JSONRenderer
import service.control

from services.token import make_admin_token

from . import (
    actions,
    handlers,
)

logger = logging.getLogger(__name__)


class SlackViewSet(viewsets.ViewSet):

    render_classes = (JSONRenderer,)

    def initial(self, request, *args, **kwargs):
        request.start_timestamp = arrow.utcnow().timestamp
        super(SlackViewSet, self).initial(request, *args, **kwargs)

    def perform_authentication(self, request, *args, **kwargs):
        logger.info('received slash command: %s', self.request.data)
        token = self.request.data['token']
        try:
            request.slash_integration = service.control.get_object(
                service='organization',
                action='get_integration',
                client_kwargs={'token': make_admin_token()},
                return_object='integration',
                integration_type=integration_pb2.SLACK_SLASH_COMMAND,
                provider_uid=token,
            )
        except service.control.CallActionError:
            # TODO if we want to get fancy we should emit a message back that
            # luno isn't properly set up.
            raise exceptions.NotAuthenticated()

        organization_token = make_admin_token(
            organization_id=request.slash_integration.organization_id,
        )
        try:
            request.api_integration = service.control.get_object(
                service='organization',
                action='get_integration',
                client_kwargs={'token': organization_token},
                return_object='integration',
                integration_type=integration_pb2.SLACK_WEB_API,
            )
            request.slack_api_token = request.api_integration.slack_web_api.token
        except service.control.CallActionError:
            # TODO we should be returning that the integration isn't properly set up
            raise exceptions.NotAuthenticated()

        try:
            request.profile = actions.get_profile_for_slack_user(
                organization_token,
                request.api_integration.slack_web_api.token,
                self.request.data['user_id'],
            )
        except service.control.CallActionError:
            # TODO we should be sending a DM to the user asking them to link their slack account
            raise exceptions.NotAuthenticated()

        request.token = make_admin_token(
            profile_id=request.profile.id,
            organization_id=request.slash_integration.organization_id,
        )

    # TODO should override handle_exception to return a text error to the user
    def slash(self, request, *args, **kwargs):
        return handlers.handle_hook(request)
