import json
import logging
import urllib

from django.conf import settings
from protobufs.services.user import containers_pb2 as user_containers
from protobufs.services.organization.containers import integration_pb2

import requests
import service.control

from services.token import make_admin_token

from . import base
from .. import models
from ..authentication import utils
from organizations import models as organization_models

logger = logging.getLogger(__name__)


class Provider(base.BaseProvider):

    type = user_containers.IdentityV1.SLACK
    provider_profile = None

    exception_to_error_map = {
        base.MissingRequiredProfileFieldError: 'PROVIDER_PROFILE_FIELD_MISSING',
    }

    @classmethod
    def get_authorization_url(cls, organization, redirect_uri, **kwargs):
        payload = {
            'domain': organization.domain,
            'redirect_uri': redirect_uri,
        }
        parameters = {
            'client_id': settings.SLACK_CLIENT_ID,
            'scope': settings.SLACK_SCOPE,
            'state': base.get_state_token(cls.type, payload=payload),
        }
        return '%s?%s' % (
            settings.SLACK_AUTHORIZATION_URL,
            urllib.urlencode(parameters),
        )

    def _get_credentials_from_code(self, code):
        parameters = {
            'client_id': settings.SLACK_CLIENT_ID,
            'client_secret': settings.SLACK_CLIENT_SECRET,
            'code': code,
        }
        response = requests.get(
            settings.SLACK_TOKEN_URL,
            params=parameters
        )
        if not response.ok:
            raise base.ExchangeError(response)

        try:
            payload = response.json()
        except ValueError:
            raise base.ExchangeError(response)
        return payload

    def complete_authorization(self, request, response, state):
        redirect_uri = state.get('redirect_uri')
        domain = state['domain']
        organization = organization_models.Organization.objects.get(
            domain=domain
        )

        authorization_code = request.oauth2_details.code
        credentials = self._get_credentials_from_code(authorization_code)

        if redirect_uri and utils.valid_redirect_uri(redirect_uri):
            response.redirect_uri = redirect_uri

        identity, _ = self.get_identity(credentials['team_id'], organization.id)
        identity.access_token = credentials['access_token']
        return identity

    def finalize_authorization(self, user, identity, request, response):
        organization = organization_models.Organization.objects.get(
            pk=identity.organization_id,
        )
        token = make_admin_token(organization_id=str(organization.id))
        client = service.control.Client('organization', token=token)
        response = client.call_action('enable_integration', integration={
            'integration_type': integration_pb2.SLACK_SLASH_COMMAND,
            'slack_slash_command': {
                'token': settings.SLACK_SLASH_COMMANDS_TOKEN,
            },
            'provider_uid': identity.provider_uid,
        })
        response = client.call_action('enable_integration', integration={
            'integration_type': integration_pb2.SLACK_WEB_API,
            'slack_web_api': {
                'token': identity.access_token,
            },
        })
