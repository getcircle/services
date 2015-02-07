import json
import urllib

import arrow
from cryptography.fernet import (
    Fernet,
    InvalidToken,
    MultiFernet,
)
from django.conf import settings
from django.utils.crypto import get_random_string
from itsdangerous import (
    BadSignature,
    TimestampSigner,
)
from linkedin import linkedin
from protobufs.user_service_pb2 import UserService
import requests
import service.control

from . import models

CSRF_KEY_LENGTH = 32


def get_state_signer(provider):
    return TimestampSigner(settings.SECRET_KEY, salt=str(provider))


def get_state_token(provider, payload):
    payload['csrftoken'] = get_random_string(CSRF_KEY_LENGTH)
    signer = get_state_signer(provider)
    encrypter = MultiFernet(map(Fernet, settings.SECRET_ENCRYPTION_KEYS))
    token = encrypter.encrypt(json.dumps(payload))
    return signer.sign(token)


def parse_state_token(provider, token):
    payload = None
    signer = get_state_signer(provider)
    crypt = MultiFernet(map(Fernet, settings.SECRET_ENCRYPTION_KEYS))
    try:
        encrypted_token = signer.unsign(token, max_age=settings.USER_SERVICE_STATE_MAX_AGE)
        payload = json.loads(
            crypt.decrypt(encrypted_token, ttl=settings.USER_SERVICE_STATE_MAX_AGE)
        )
    except (BadSignature, InvalidToken, ValueError):
        # XXX we should be logging what went wrong here
        payload = None
    return payload


class ExchangeError(Exception):
    """Exception raised when there is an error exchanging authorization code for access token"""

    def __init__(self, response, *args, **kwargs):
        self.response = response
        super(ExchangeError, self).__init__(*args, **kwargs)


class MissingRequiredProfileFieldError(Exception):
    """Exception raised when a required profile field is missing"""


class LinkedIn(object):

    type = UserService.LINKEDIN
    profile_selectors = (
        'id',
        'first-name',
        'last-name',
        'formatted-name',
        'phonetic-first-name',
        'phonetic-last-name',
        'formatted-phonetic-name',
        'headline',
        'location',
        'industry',
        'num-connections',
        'num-connections-capped',
        'summary',
        'specialties',
        'positions',
        'picture-url',
        'public-profile-url',
        'email-address',
        'associations',
        'interests',
        'publications',
        'patents',
        'languages',
        'skills',
        'certifications',
        'educations',
        'courses',
        'volunteer',
        'num-recommenders',
        'recommendations-received',
        'date-of-birth',
        'honors-awards',
        'phone-numbers',
        'main-address',
        'twitter-accounts',
        'primary-twitter-account',
        'projects',
    )

    exception_to_error_map = {
        linkedin.LinkedInError: 'PROVIDER_API_ERROR',
        MissingRequiredProfileFieldError: 'PROVIDER_PROFILE_FIELD_MISSING',
    }

    def __init__(self, token):
        self.token = token

    @classmethod
    def get_authorization_url(self, token=None):
        payload = {}
        if token:
            payload['token'] = token

        parameters = {
            'response_type': 'code',
            'scope': settings.LINKEDIN_SCOPE,
            'client_id': settings.LINKEDIN_CLIENT_ID,
            'redirect_uri': settings.LINKEDIN_REDIRECT_URI,
            'state': get_state_token(self.type, payload=payload),
        }
        return '%s?%s' % (
            settings.LINKEDIN_AUTHORIZATION_URL,
            urllib.urlencode(parameters),
        )

    def get_exchange_url(self, oauth2_details):
        parameters = {
            'grant_type': 'authorization_code',
            'code': oauth2_details.code,
            'redirect_uri': settings.LINKEDIN_REDIRECT_URI,
            'client_id': settings.LINKEDIN_CLIENT_ID,
            'client_secret': settings.LINKEDIN_CLIENT_SECRET,
        }
        return '%s?%s' % (
            settings.LINKEDIN_ACCESS_TOKEN_URL,
            urllib.urlencode(parameters),
        )

    def get_identity(self, provider_uid):
        identity = models.Identity.objects.get_or_none(
            provider_uid=provider_uid,
            provider=self.type,
        )
        if identity is None:
            identity = models.Identity(provider=self.type, provider_uid=provider_uid)
        return identity

    def complete_authorization(self, oauth2_details):
        url = self.get_exchange_url(oauth2_details)
        token, expires_in = self._get_access_token(url)
        application = linkedin.LinkedInApplication(token=token)
        profile = application.get_profile(selectors=self.profile_selectors)
        self._add_skills_to_profile(profile)

        provider_uid = self._extract_required_profile_field(
            profile,
            'id',
            alias='provider_uid',
        )
        identity = self.get_identity(provider_uid)
        identity.full_name = self._extract_required_profile_field(
            profile,
            'formattedName',
            alias='full_name',
        )
        identity.email = self._extract_required_profile_field(
            profile,
            'emailAddress',
            alias='email_address',
        )
        identity.data = json.dumps(profile)
        identity.access_token = token
        identity.expires_at = arrow.utcnow().timestamp + expires_in
        return identity

    def _add_skills_to_profile(self, data):
        if not self.token.profile_id:
            return None

        linkedin_skills = data.get('skills', {}).get('values', [])
        internal_skills = []
        for linkedin_skill in linkedin_skills:
            internal_skill = linkedin_skill.get('skill')
            if internal_skill:
                internal_skills.append(internal_skill)

        client = service.control.Client('profile', token=self.token._token)
        try:
            client.call_action(
                'add_skills',
                profile_id=self.token.profile_id,
                skills=internal_skills,
            )
        except client.CallActionError:
            pass
        return None

    def _extract_required_profile_field(self, profile, field_name, alias=None):
        try:
            value = profile[field_name]
        except KeyError:
            alias = alias or field_name
            raise MissingRequiredProfileFieldError(alias)
        return value

    def _get_access_token(self, url):
        response = requests.post(url)
        if not response.ok:
            raise ExchangeError(response)

        try:
            payload = response.json()
        except ValueError:
            raise ExchangeError(response)

        return payload['access_token'], payload['expires_in']
