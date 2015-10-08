from onboarding.parsers.locations import add_locations
from onboarding.parsers.profiles import add_profiles
from services.management.base import BaseCommand
from ..utils import get_token_for_domain


class Command(BaseCommand):

    help = 'Load locations and profile for an organization'

    def add_arguments(self, parser):
        parser.add_argument('organization_domain', type=str, help='Organization\'s domain')
        parser.add_argument('profiles_filename', help='Filename with profile data we\'re adding')
        parser.add_argument('locations_filename', help='Filename with location data we\'re adding')

    def handle(self, *args, **options):
        organization_domain = options['organization_domain']
        profiles_filename = options['profiles_filename']
        locations_filename = options['locations_filename']

        token = get_token_for_domain(organization_domain)
        add_locations(locations_filename, token)
        add_profiles(profiles_filename, token)
