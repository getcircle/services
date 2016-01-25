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
from protobufs.services.organization.containers import sso_pb2
import requests
import service.control

from services.token import make_admin_token

from . import base
from .. import models
from ..authentication import utils

logger = logging.getLogger(__name__)


class GoogleSSONotEnabled(Exception):
    pass


class DomainNotVerified(Exception):
    pass


class AuthenticationFailed(Exception):
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

        authorization_code = request.oauth2_details.code
        credentials = self._get_credentials_from_code(
            authorization_code,
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

    def authenticate(self, code, id_token, organization):
        try:
            get_sso_for_domain(organization.domain)
        except GoogleSSONotEnabled:
            raise AuthenticationFailed

        try:
            id_token = verify_id_token(id_token, settings.GOOGLE_CLIENT_ID)
        except AppIdentityError:
            logger.error('error verifying token')
            raise AuthenticationFailed

        identity, new = self.get_identity(id_token['sub'], organization.id)
        if new:
            logger.error('identity not found', extra={
                'data': {
                    'id_token': id_token,
                    'organization_domain': organization.domain,
                },
            })
            raise AuthenticationFailed

        try:
            user = models.User.objects.get(pk=identity.user_id, organization_id=organization.id)
        except models.User.DoesNotExist:
            raise AuthenticationFailed
        return user

    def _get_name_from_provider(self):
        first_name = None
        last_name = None
        if self.provider_profile:
            try:
                first_name = self.provider_profile['name']['givenName']
                last_name = self.provider_profile['name']['familyName']
            except KeyError:
                pass

            if not first_name or not last_name:
                try:
                    first_name, last_name = self.provider_profile['displayName'].split(' ', 1)
                except ValueError:
                    pass

        return first_name, last_name

    def finalize_authorization(self, user, identity, request, response):
        token = make_admin_token(organization_id=user.organization_id, user_id=user.id)
        first_name, last_name = self._get_name_from_provider()
        try:
            service.control.call_action(
                service='profile',
                action='create_profile',
                client_kwargs={'token': token},
                profile={
                    'email': user.primary_email,
                    'authentication_identifier': user.primary_email,
                    'first_name': first_name,
                    'last_name': last_name,
                },
            )
        except service.control.CallActionError as e:
            if 'DUPLICATE' not in e.response.errors:
                raise

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
