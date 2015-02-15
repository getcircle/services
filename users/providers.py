import httplib2
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
from oauth2client import GOOGLE_TOKEN_URI
from oauth2client.client import (
    AccessTokenRefreshError,
    credentials_from_code,
    FlowExchangeError,
    OAuth2Credentials,
    verify_id_token,
)
from oauth2client.crypt import AppIdentityError
from protobufs.resume_service_pb2 import ResumeService
from protobufs.user_service_pb2 import UserService
import requests
import service.control
from service import actions

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


class ImproperlyConfiguredError(Exception):
    """Exception raised when a provider isn't configured correctly"""


class BaseProvider(object):

    type = None
    csrf_exempt = False

    def __init__(self, token):
        self.token = token
        if self.type is None:
            raise ImproperlyConfiguredError

    def get_identity(self, provider_uid):
        new = False
        identity = models.Identity.objects.get_or_none(
            provider_uid=provider_uid,
            provider=self.type,
        )
        if identity is None:
            new = True
            identity = models.Identity(provider=self.type, provider_uid=provider_uid)
        return identity, new

    @classmethod
    def get_authorization_url(self, token=None):
        raise NotImplementedError('Subclasses must override this method')

    def complete_authorization(self, request):
        raise NotImplementedError('Subclasses must override this method')

    def finalize_authorization(self, identity, user):
        pass

    def _extract_required_profile_field(self, profile, field_name, alias=None):
        try:
            value = profile[field_name]
        except KeyError:
            alias = alias or field_name
            raise MissingRequiredProfileFieldError(alias)
        return value


class LinkedIn(BaseProvider):

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

    def __init__(self, *args, **kwargs):
        super(LinkedIn, self).__init__(*args, **kwargs)

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

    def complete_authorization(self, request):
        url = self.get_exchange_url(request.oauth2_details)
        token, expires_in = self._get_access_token(url)
        application = linkedin.LinkedInApplication(token=token)
        self.profile = application.get_profile(selectors=self.profile_selectors)
        self._add_skills_to_profile(self.profile)

        provider_uid = self._extract_required_profile_field(
            self.profile,
            'id',
            alias='provider_uid',
        )
        identity, _ = self.get_identity(provider_uid)
        identity.full_name = self._extract_required_profile_field(
            self.profile,
            'formattedName',
            alias='full_name',
        )
        identity.email = self._extract_required_profile_field(
            self.profile,
            'emailAddress',
            alias='email_address',
        )
        identity.data = json.dumps(self.profile)
        identity.access_token = token
        identity.expires_at = arrow.utcnow().timestamp + expires_in
        return identity

    def finalize_authorization(self, identity, user):
        self._create_resume(user, self.profile)

    def _copy_approximate_date_to_container(self, date, container):
        if 'year' in date:
            container.year = date['year']
        if 'month' in date:
            container.month = date['month']
        if 'day' in date:
            container.day = date['day']

    def _create_educations(self, user, data):
        educations = data.get('educations', {}).get('values', [])
        containers = []
        for education in educations:
            container = ResumeService.Containers.Education()
            container.user_id = str(user.id)
            end_date = education.get('endDate')
            if end_date:
                self._copy_approximate_date_to_container(end_date, container.end_date)
            start_date = education.get('startDate')
            if start_date:
                self._copy_approximate_date_to_container(start_date, container.start_date)

            if 'activities' in education:
                container.activities = education['activities']
            if 'notes' in education:
                container.notes = education['notes']
            if 'fieldOfStudy' in education:
                container.field_of_study = education['fieldOfStudy']
            if 'degree' in education:
                container.degree = education['degree']
            if 'schoolName' in education:
                container.school_name = education['schoolName']
            containers.append(container)

        client = service.control.Client('resume', token=self.token._token)
        client.call_action('bulk_create_educations', educations=containers)

    def _create_positions(self, user, data):
        positions = data.get('positions', {}).get('values', [])
        companies = []
        for position in positions:
            if 'company' in position:
                company = {
                    'linkedin_id': str(position['company']['id']),
                    'name': position['company']['name'],
                }
                companies.append(company)

        client = service.control.Client('resume', token=self.token._token)
        response = client.call_action('bulk_create_companies', companies=companies)
        company_dict = dict((company.name, company) for company in response.result.companies)

        containers = []
        for position in positions:
            container = ResumeService.Containers.Position()
            container.user_id = str(user.id)
            end_date = position.get('endDate')
            if end_date:
                self._copy_approximate_date_to_container(end_date, container.end_date)
            start_date = position.get('startDate')
            if start_date:
                self._copy_approximate_date_to_container(start_date, container.start_date)

            if 'title' in position:
                container.title = position['title']

            if 'summary' in position:
                container.summary = position['summary']

            if 'company' in position and position['company']['name'] in company_dict:
                container.company.CopyFrom(company_dict[position['company']['name']])

            containers.append(container)
        client.call_action('bulk_create_positions', positions=containers)

    def _create_resume(self, user, data):
        if not self.token:
            return None

        self._create_educations(user, data)
        self._create_positions(user, data)

    def _add_skills_to_profile(self, data):
        if not self.token or not self.token.profile_id:
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

    def _get_access_token(self, url):
        response = requests.post(url)
        if not response.ok:
            raise ExchangeError(response)

        try:
            payload = response.json()
        except ValueError:
            raise ExchangeError(response)

        return payload['access_token'], payload['expires_in']


class Google(BaseProvider):

    type = UserService.GOOGLE
    csrf_exempt = True

    exception_to_error_map = {
        FlowExchangeError: 'PROVIDER_API_ERROR',
        MissingRequiredProfileFieldError: 'PROVIDER_PROFILE_FIELD_MISSING',
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
            raise ExchangeError(response)

        try:
            payload = response.json()
        except ValueError:
            raise ExchangeError(response)
        return payload

    def _get_credentials_from_code(self, identity, request):
        credentials = credentials_from_code(
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            scope=settings.GOOGLE_SCOPE,
            code=request.oauth_sdk_details.code,
            redirect_uri='',
        )
        identity.email = self._extract_required_profile_field(credentials.id_token, 'email')
        identity.expires_at = arrow.get(credentials.token_expiry).timestamp
        identity.access_token = credentials.access_token
        identity.refresh_token = credentials.refresh_token
        return credentials

    def _update_identity_access_token(self, identity, access_token, token_expiry):
        identity.expires_at = arrow.get(token_expiry).timestamp
        identity.access_token = access_token

    def complete_authorization(self, request):
        try:
            id_token = verify_id_token(
                request.oauth_sdk_details.id_token,
                settings.GOOGLE_CLIENT_ID,
            )
        except AppIdentityError:
            raise actions.Action.ActionFieldError('oauth_sdk_details.id_token', 'INVALID')

        identity, new = self.get_identity(id_token['sub'])
        if new:
            credentials = self._get_credentials_from_code(identity, request)
        else:
            credentials = self._get_credentials_from_identity(identity)

        try:
            token_info = credentials.get_access_token()
        except AccessTokenRefreshError:
            # Token has expired based on expiry time
            # Attempt to fetch new credentials based on the code submitted by the client
            credentials = self._get_credentials_from_code(identity, request)
            token_info = credentials.get_access_token()

        if token_info.access_token != identity.access_token:
            self._update_identity_access_token(
                identity,
                token_info.access_token,
                credentials.token_expiry,
            )

        try:
            profile = self._get_profile(token_info.access_token)
        except ExchangeError as e:
            if e.response.status_code == 401:
                # Token has been revoked
                # Attempt to refresh the credentials
                try:
                    credentials.refresh(httplib2.Http())
                except AccessTokenRefreshError:
                    credentials = self._get_credentials_from_code(identity, request)

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
