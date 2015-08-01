from __future__ import absolute_import

import arrow
import json
import urllib

from django.conf import settings
import requests
import service.control

from linkedin import linkedin
from protobufs.services.profile import containers_pb2 as profile_containers
from protobufs.services.user import containers_pb2 as user_containers

from . import base


class Provider(base.BaseProvider):

    type = user_containers.IdentityV1.LINKEDIN
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
        base.MissingRequiredProfileFieldError: 'PROVIDER_PROFILE_FIELD_MISSING',
    }

    @classmethod
    def get_authorization_url(self, token=None, additional_scopes='', **kwargs):
        payload = {}
        if token:
            payload['token'] = token

        scope = ' '.join([settings.LINKEDIN_SCOPE, additional_scopes]).strip()
        parameters = {
            'response_type': 'code',
            'scope': scope,
            'client_id': settings.LINKEDIN_CLIENT_ID,
            'redirect_uri': settings.LINKEDIN_REDIRECT_URI,
            'state': base.get_state_token(self.type, payload=payload),
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

    def complete_authorization(self, request, response):
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

    def _copy_approximate_date_to_container(self, date, container):
        if 'year' in date:
            container.year = date['year']
        if 'month' in date:
            container.month = date['month']
        if 'day' in date:
            container.day = date['day']

    def _add_skills_to_profile(self, data):
        if not self.token or not self.token.profile_id:
            return None

        linkedin_skills = data.get('skills', {}).get('values', [])
        internal_skills = []
        for linkedin_skill in linkedin_skills:
            internal_skill = linkedin_skill.get('skill')
            internal_skill['tag_type'] = profile_containers.TagV1.SKILL
            if internal_skill:
                internal_skills.append(internal_skill)

        client = service.control.Client('profile', token=self.token._token)
        try:
            client.call_action(
                'add_tags',
                profile_id=self.token.profile_id,
                tags=internal_skills,
            )
        except service.control.CallActionError:
            pass
        return None

    def _get_access_token(self, url):
        response = requests.post(url)
        if not response.ok:
            raise base.ExchangeError(response)

        try:
            payload = response.json()
        except ValueError:
            raise base.ExchangeError(response)

        return payload['access_token'], payload['expires_in']
