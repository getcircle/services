from __future__ import absolute_import

import arrow
import json
import urllib

from django.conf import settings
import requests
import service.control

from linkedin import linkedin
from protobufs.services.profile import containers_pb2 as profile_containers
from protobufs.services.resume import containers_pb2 as resume_containers
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
            container = resume_containers.EducationV1()
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
                    'name': position['company']['name'],
                }
                if 'id' in position['company']:
                    company['linkedin_id'] = str(position['company']['id'])
                companies.append(company)

        client = service.control.Client('resume', token=self.token._token)
        response = client.call_action('bulk_create_companies', companies=companies)
        company_dict = dict((company.name, company) for company in response.result.companies)

        containers = []
        for position in positions:
            container = resume_containers.PositionV1()
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
        except client.CallActionError:
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
