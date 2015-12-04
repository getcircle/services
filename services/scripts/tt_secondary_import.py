import hashlib
import os

import arrow
import boto3
from django.conf import settings
from django.db import transaction
import requests
import service.control

from onboarding.parsers.users import add_users
from services.token import get_token_for_domain

from profiles.models import Profile

from ..bootstrap import Bootstrap

API_URL = 'https://thumbtack.okta.com/api/v1/users'
AUTHORIZATION_HEADER = os.environ['AUTHORIZATION_HEADER']
IMAGE_URL = 'https://thumbtack.bamboohr.com/employees/photos/?h=%s'


def get_image_key(profile_id):
    return 'profiles/%s' % (hashlib.md5(arrow.utcnow().isoformat() + ':' + profile_id).hexdigest(),)


def fetch_all_profiles(url=None):
    profiles = []

    if not url:
        url = API_URL

    print '--> requesting: %s' % (url,)
    response = requests.get(url, headers={'Authorization': AUTHORIZATION_HEADER})
    for user in response.json():
        profiles.append(user['profile'])

    if response.links.get('next'):
        profiles.extend(fetch_all_profiles(response.links['next']['url']))
    return profiles


def is_valid_okta_profile(profile):
    return bool(
        profile.get('locale') in ('TSF', 'TSL') and
        profile.get('employeeNumber', '') != ''
    )


def construct_dn(profile):
    first_name = profile['firstName']
    last_name = profile['lastName']
    return 'CN=%s,OU=FTE,OU=%s,OU=Users,OU=Thumbtack,DC=corp,DC=thumbtack,DC=com' % (
        ' '.join([first_name, last_name]),
        profile['locale'],
    )


def sync_bamboo_hr_image(profile):
    response = requests.get(IMAGE_URL % (hashlib.md5(profile.email.lower()).hexdigest(),))
    if len(response.content) != 2778:
        key = get_image_key(str(profile.id))
        client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )
        client.put_object(
            Body=response.content,
            Bucket='lunohq-media',
            ContentType='image/png',
            Key=key,
        )
        return 'https://s3.amazonaws.com/lunohq-media/%s' % (key,)


def get_valid_profiles():
    profiles = fetch_all_profiles()
    return [profile for profile in profiles if is_valid_okta_profile(profile)]


@transaction.atomic
def sync_profiles(okta_profiles, token):
    for okta_profile in okta_profiles:
        okta_profile['dn'] = construct_dn(okta_profile)

    employee_number_to_okta_profile = dict((p['employeeNumber'], p) for p
                                           in okta_profiles if p.get('employeeNumber'))
    dn_to_profile = dict((p['dn'], p) for p in okta_profiles)
    profiles = Profile.objects.filter(organization_id='4d3ec6da-1c34-4880-bc92-a2ec7d35b073')
    en_to_profile = dict((p.authentication_identifier, p) for p in profiles)

    direct_reports = {}

    TSL = '25365f3f-3c52-4548-9c2b-9c622fef3570'
    TSF = 'cf5015ce-17f3-4a2b-8316-8a6b1ae0bcc9'
    location_members = {
        TSL: [],
        TSF: [],
    }

    def should_update_manager(profile):
        today = arrow.utcnow().floor('day')
        if profile.changed >= today:
            return True
        elif profile.changed <= arrow.get('2015-10-20'):
            return True
        return False

    users_to_delete = []
    for profile in profiles:
        print 'parsing profile: %s (%s)' % (profile.email, profile.id)
        okta_profile = employee_number_to_okta_profile.get(profile.authentication_identifier)
        if not okta_profile:
            if not profile.email.endswith('lunohq.com'):
                users_to_delete.append(profile.id)
            continue

        if 'manager' in okta_profile:
            if should_update_manager(profile):
                manager = dn_to_profile.get(okta_profile['manager'])
                if not manager:
                    print 'manager not found: %s' % (okta_profile['manager'],)
                    continue

                manager_profile = en_to_profile[manager['employeeNumber']]
                direct_reports.setdefault(str(manager_profile.id), []).append(str(profile.id))

        if 'locale' in okta_profile and okta_profile['locale'] in ('TSL', 'TSF'):
            if okta_profile['locale'] == 'TSF':
                location_members[TSF].append(str(profile.id))
            elif okta_profile['locale'] == 'TSL':
                location_members[TSL].append(str(profile.id))

        changed = {}
        title = okta_profile.get('title')
        if title and title != profile.title:
            changed[profile.title] = title
            profile.title = title

        first_name = okta_profile.get('firstName')
        if first_name and first_name != profile.first_name:
            changed[profile.first_name] = first_name
            profile.first_name = first_name

        last_name = okta_profile.get('lastName')
        if last_name and last_name != profile.last_name:
            changed[profile.last_name] = last_name
            profile.last_name = last_name

        image_url = sync_bamboo_hr_image(profile)
        if image_url:
            changed['image_url'] = image_url
            profile.image_url = image_url

        if changed:
            fields = ['%s -> %s' % (k, v) for k, v in changed.iteritems()]
            print 'adjusting profile: %s\n\t%s' % (
                profile.email,
                '\n\t'.join(fields),
            )
            profile.save()

    #for key, value in direct_reports.iteritems():
        #service.control.call_action(
            #service='organization',
            #action='add_direct_reports',
            #client_kwargs={'token': token},
            #profile_id=key,
            #direct_reports_profile_ids=value,
        #)

    #for key, value in location_members.iteritems():
        #service.control.call_action(
            #service='organization',
            #action='add_location_members',
            #client_kwargs={'token': token},
            #location_id=key,
            #profile_ids=value,
        #)

    print 'delete users: %s' % (users_to_delete,)


def run():
    Bootstrap.bootstrap()
    token = get_token_for_domain('thumbtack')
    profiles = get_valid_profiles()
    sync_profiles(profiles, token)
