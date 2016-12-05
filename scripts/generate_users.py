"""Script for creating fake users in dev within an organization.

Run with:

    $ python manage.py runscript generate_users --script-args team 10

"""
import logging

from django.conf import settings
import requests

from services.bootstrap import Bootstrap

from organizations.models import Organization
from profiles.models import Profile
from users.models import User

logger = logging.getLogger(__name__)


def generate_fake_user(organization_id, fake_data):
    user = User.objects.create(
        primary_email=fake_data['email'],
        organization_id=organization_id,
    )
    profile = Profile.objects.create(
        user_id=user.id,
        organization_id=organization_id,
        email=fake_data['email'],
        first_name=fake_data['name']['first'].capitalize(),
        last_name=fake_data['name']['last'].capitalize(),
        image_url=fake_data['picture']['medium'],
        authentication_identifier=fake_data['email'],
    )
    return (user, profile)


def generate_fake_users(domain, number_of_users):
    endpoint = 'https://randomuser.me/api/?results=%s&nat=us' % (number_of_users,)
    response = requests.get(endpoint)
    if not response.ok:
        logger.error('invalid response: %s - %s', response.status_code, response.reason)
        return

    users = []
    organization = Organization.objects.get(domain=domain)
    for fake_data in response.json()['results']:
        user = generate_fake_user(organization.id, fake_data['user'])
        users.append(user)
    return users


def run(domain, number_of_users):
    if not settings.DEBUG:
        logger.error('can\'t generate fake users in production')
        return

    Bootstrap.bootstrap()
    generate_fake_users(domain, number_of_users)

    logger.info('generated %s users in %s', number_of_users, domain)
