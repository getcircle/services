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
import requests
import service.control
from service import actions

from . import base


class Provider(base.BaseProvider):

    type = user_containers.IdentityV1.GOOGLE
    csrf_exempt = True

    exception_to_error_map = {
        FlowExchangeError: 'PROVIDER_API_ERROR',
        base.MissingRequiredProfileFieldError: 'PROVIDER_PROFILE_FIELD_MISSING',
        AccessTokenRefreshError: 'TOKEN_EXPIRED',
    }

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

    def _get_profile(self, access_token):
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
        }
        # NB: For native app SDKs, Google requires a redirect_uri of an empty string
        if is_sdk:
            parameters['redirect_uri'] = ''
        elif client_type == token_pb2.WEB:
            parameters['redirect_uri'] = 'postmessage'
        else:
            parameters['redirect_uri'] = settings.GOOGLE_REDIRECT_URI

        logging.getLogger('user:providers:google').info('requesting credentials: %s', parameters)
        credentials = credentials_from_code(**parameters)
        if id_token is not None:
            credentials.id_token = id_token
        if identity:
            self._update_identity_with_credentials(identity, credentials)
        return credentials

    def _update_identity_with_credentials(self, identity, credentials):
        identity.email = self._extract_required_profile_field(credentials.id_token, 'email')
        identity.expires_at = arrow.get(credentials.token_expiry).timestamp
        identity.access_token = credentials.access_token
        identity.refresh_token = credentials.refresh_token

    def _update_identity_access_token(self, identity, access_token, token_expiry):
        identity.expires_at = arrow.get(token_expiry).timestamp
        identity.access_token = access_token

    def _get_authorization_code(self, request):
        if request.HasField('oauth2_details'):
            return request.oauth2_details.code
        else:
            return request.oauth_sdk_details.code

    def _get_identity_and_credentials_oauth2(self, request):
        credentials = self._get_credentials_from_code(
            self._get_authorization_code(request),
            client_type=request.client_type,
        )
        identity, new = self.get_identity(credentials.id_token['sub'])
        self._update_identity_with_credentials(identity, credentials)
        return identity, credentials

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

    def complete_authorization(self, request, response):
        authorization_code = self._get_authorization_code(request)
        is_sdk = request.HasField('oauth_sdk_details')
        if is_sdk:
            identity, credentials = self._get_identity_and_credentials_oauth_sdk(request)
        else:
            identity, credentials = self._get_identity_and_credentials_oauth2(request)
            # include the details to authenticate via the sdk in the response
            response.oauth_sdk_details.code = authorization_code
            response.oauth_sdk_details.id_token = credentials.token_response.get('id_token', '')

        try:
            token_info = credentials.get_access_token()
        except AccessTokenRefreshError:
            # Token has expired based on expiry time
            # Attempt to fetch new credentials based on the code submitted by the client
            credentials = self._get_credentials_from_code(
                authorization_code,
                identity=identity,
                is_sdk=is_sdk,
                client_type=request.client_type,
            )
            token_info = credentials.get_access_token()

        if token_info.access_token != identity.access_token:
            self._update_identity_access_token(
                identity,
                token_info.access_token,
                credentials.token_expiry,
            )

        try:
            profile = self._get_profile(token_info.access_token)
        except base.ExchangeError as e:
            if e.response.status_code == 401:
                # Token has been revoked
                # Attempt to refresh the credentials
                try:
                    credentials.refresh(httplib2.Http())
                except AccessTokenRefreshError:
                    credentials = self._get_credentials_from_code(
                        authorization_code,
                        identity=identity,
                        is_sdk=is_sdk,
                        client_type=request.client_type,
                    )

                self._update_identity_access_token(
                    identity,
                    credentials.access_token,
                    credentials.token_expiry,
                )
                profile = self._get_profile(credentials.access_token)

        identity.full_name = self._extract_required_profile_field(
            profile,
            'displayName',
            alias='full_name',
        )
        identity.data = json.dumps(profile)
        return identity

    @classmethod
    def get_authorization_url(self, token=None, **kwargs):
        payload = {}
        if token:
            payload['token'] = token

        scope = settings.GOOGLE_SCOPE.strip()
        parameters = {
            'response_type': 'code',
            'scope': scope,
            'client_id': settings.GOOGLE_CLIENT_ID,
            'redirect_uri': settings.GOOGLE_REDIRECT_URI,
            'state': base.get_state_token(self.type, payload=payload),
            'access_type': 'offline',
        }
        if kwargs.get('login_hint'):
            parameters['login_hint'] = kwargs['login_hint']

        return '%s?%s' % (
            settings.GOOGLE_AUTHORIZATION_URL,
            urllib.urlencode(parameters),
        )

    def revoke(self, identity):
        response = requests.get(
            settings.GOOGLE_REVOKE_TOKEN_URL,
            params={'token': identity.access_token},
        )
        if not response.ok:
            raise base.ProviderAPIError(response)

        # NB: Since google is our primary form of auth, ensure the user is logged out
        client = service.control.Client('user', token=self.token)
        client.call_action('logout', revoke_all=True)
