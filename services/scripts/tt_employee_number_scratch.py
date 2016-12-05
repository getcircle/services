import os
import requests

API_URL = 'https://thumbtack.okta.com/api/v1/users'
AUTHORIZATION_HEADER = os.environ['AUTHORIZATION_HEADER']


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


@transaction.atomic
def run():
    okta_profiles = fetch_all_profiles()
    employee_numbers = filter(lambda x: x.get('employeeNumber', ''), okta_profiles)
    profiles = Profile.objects.filter(organization_id='4d3ec6da-1c34-4880-bc92-a2ec7d35b073')
    profiles_dict = dict((profile.email, profile) for profile in profiles)
    for profile in employee_numbers:
        luno_profile = profiles_dict.get(profile['email'])
        if not luno_profile:
            continue
        else:
            print '--> adjusting authentication_identifier for: %s (%s) from %s to %s' % (
                luno_profile.email,
                luno_profile.id,
                luno_profile.authentication_identifier,
                profile['employeeNumber'],
            )
            Profile.objects.filter(
                pk=luno_profile.pk,
                organization_id='4d3ec6da-1c34-4880-bc92-a2ec7d35b073',
            ).update(authentication_identifier=profile['employeeNumber'])
