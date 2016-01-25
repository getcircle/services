import json
import logging
import urllib

import arrow
from django.conf import settings
import httplib2
from oauth2client import GOOGLE_TOKEN_URI
from oauth2client.client import (
    AccessTokenRefreshError,
    credentials_from_code,
    FlowExchangeError,
    OAuth2Credentials,
    verify_id_token,
)
from oauth2client.crypt import AppIdentityError
from protobufs.services.user import containers_pb2 as user_containers
from protobufs.services.user.containers import token_pb2
from protobufs.services.organization.containers import sso_pb2
import requests
import service.control
from service import actions

from . import base
from ..authentication import utils

logger = logging.getLogger(__name__)


class GoogleSSONotEnabled(Exception):
    pass


class DomainNotVerified(Exception):
    pass


def get_sso_for_domain(domain):
    try:
        sso = service.control.get_object(
            service='organization',
            action='get_sso',
            organization_domain=domain,
            return_object='sso',
        )
        if not sso.provider == sso_pb2.GOOGLE:
            raise GoogleSSONotEnabled
    except service.control.CallActionError:
        raise GoogleSSONotEnabled
    return sso


def _fetch_provider_profile(access_token):
    response = requests.get(
        settings.GOOGLE_PROFILE_URL,
        headers={'Authorization': 'Bearer %s' % (access_token,)},
    )
    if not response.ok:
        raise base.ExchangeError(response)

    try:
        payload = response.json()
    except ValueError:
        raise base.ExchangeError(response)
    return payload


class Provider(base.BaseProvider):

    type = user_containers.IdentityV1.GOOGLE
    provider_profile = None

    exception_to_error_map = {
        FlowExchangeError: 'PROVIDER_API_ERROR',
        base.MissingRequiredProfileFieldError: 'PROVIDER_PROFILE_FIELD_MISSING',
        AccessTokenRefreshError: 'TOKEN_EXPIRED',
        DomainNotVerified: 'INVALID_DOMAIN',
    }

    @classmethod
    def get_authorization_url(cls, organization, sso=None, redirect_uri=None, **kwargs):
        if not sso:
            sso = get_sso_for_domain(organization.domain)

        payload = {
            'domain': organization.domain,
        }
        if redirect_uri:
            payload['redirect_uri'] = redirect_uri

        scope = settings.GOOGLE_SCOPE.strip()
        parameters = {
            'response_type': 'code',
            'scope': scope,
            'client_id': settings.GOOGLE_CLIENT_ID,
            'redirect_uri': settings.GOOGLE_REDIRECT_URI,
            'state': base.get_state_token(cls.type, payload=payload),
            'access_type': 'offline',
        }
        if kwargs.get('login_hint'):
            parameters['login_hint'] = kwargs['login_hint']

        return '%s?%s' % (
            settings.GOOGLE_AUTHORIZATION_URL,
            urllib.urlencode(parameters),
        )

    def _get_credentials_from_identity(self, identity):
        return OAuth2Credentials(
            identity.access_token,
            settings.GOOGLE_CLIENT_ID,
            settings.GOOGLE_CLIENT_SECRET,
            identity.refresh_token,
            arrow.get(identity.expires_at).naive,
            GOOGLE_TOKEN_URI,
            settings.GOOGLE_USER_AGENT,
        )

    def _fetch_provider_profile(self, access_token):
        self.provider_profile = _fetch_provider_profile(access_token)

    def _get_credentials_from_code(
            self,
            code,
            identity=None,
            id_token=None,
            is_sdk=False,
            client_type=None,
        ):
        parameters = {
            'client_id': settings.GOOGLE_CLIENT_ID,
            'client_secret': settings.GOOGLE_CLIENT_SECRET,
            'scope': settings.GOOGLE_SCOPE,
            'code': code,
            'redirect_uri': settings.GOOGLE_REDIRECT_URI,
        }
        credentials = credentials_from_code(**parameters)
        if id_token is not None:
            credentials.id_token = id_token
        if identity:
            self._update_identity_with_credentials(identity, credentials)
        return credentials

    def _update_identity_with_credentials(self, identity, credentials):
        identity.email = self.extract_required_profile_field(credentials.id_token, 'email')
        identity.expires_at = arrow.get(credentials.token_expiry).timestamp
        identity.access_token = credentials.access_token
        identity.refresh_token = credentials.refresh_token

    def _update_identity_access_token(self, identity, access_token, token_expiry):
        identity.expires_at = arrow.get(token_expiry).timestamp
        identity.access_token = access_token

    def _get_authorization_code(self, request):
        if request.oauth2_details.ByteSize():
            return request.oauth2_details.code
        else:
            return request.oauth_sdk_details.code

    def _get_identity_and_credentials_oauth_sdk(self, request):
        try:
            id_token = verify_id_token(
                request.oauth_sdk_details.id_token,
                settings.GOOGLE_CLIENT_ID,
            )
        except AppIdentityError:
            raise actions.Action.ActionFieldError('oauth_sdk_details.id_token', 'INVALID')

        identity, new = self.get_identity(id_token['sub'])
        if new:
            credentials = self._get_credentials_from_code(
                self._get_authorization_code(request),
                identity=identity,
                id_token=id_token,
                is_sdk=True,
                client_type=request.client_type,
            )
        else:
            credentials = self._get_credentials_from_identity(identity)
        return identity, credentials

    def complete_authorization(self, request, response, state):
        """Complete the authorization from Google.

        After the user successfully logs in with google, we'll receive the
        `user.containers.OAuth2DetailsV1` object (`oauth2_details`). We use
        these to:
            - retrieve the profile from Google
            - create or update an Identity for the user
            - return credentials the user can then use to authenticate with
            Google in the future.

        """
        redirect_uri = state.get('redirect_uri')
        domain = state['domain']
        sso = get_sso_for_domain(domain)

        authorization_code = self._get_authorization_code(request)
        credentials = self._get_credentials_from_code(
            authorization_code,
            client_type=request.client_type,
        )
        identity, _ = self.get_identity(credentials.id_token['sub'], sso.organization_id)
        self._update_identity_with_credentials(identity, credentials)

        if redirect_uri and utils.valid_redirect_uri(redirect_uri):
            response.redirect_uri = redirect_uri

        token_info = credentials.get_access_token()

        try:
            self._fetch_provider_profile(token_info.access_token)
        except base.ExchangeError as e:
            if e.response.status_code == 401:
                credentials.refresh(httplib2.Http())
                self._update_identity_access_token(
                    identity,
                    credentials.access_token,
                    credentials.token_expiry,
                )
                self._fetch_provider_profile(credentials.access_token)

        provider_domain = self.extract_required_profile_field(self.provider_profile, 'domain')
        if provider_domain not in sso.google.domains:
            logger.error(
                'unverified domain attempt: %s [%s]',
                self.provider_profile['domain'],
                list(sso.google.domains),
            )
            raise DomainNotVerified

        identity.full_name = self.extract_required_profile_field(
            self.provider_profile,
            'displayName',
            alias='full_name',
        )
        identity.data = json.dumps(self.provider_profile)

        # include details to authenticate via google
        response.google_credentials.code = authorization_code
        response.google_credentials.id_token = credentials.token_response.get('id_token', '')
        return identity

    def revoke(self, identity, token):
        response = requests.get(
            settings.GOOGLE_REVOKE_TOKEN_URL,
            params={'token': identity.access_token},
        )
        if not response.ok:
            raise base.ProviderAPIError(response)

        # NB: Since google is our primary form of auth, ensure the user is logged out
        client = service.control.Client('user', token=token)
        client.call_action('logout', revoke_all=True)
