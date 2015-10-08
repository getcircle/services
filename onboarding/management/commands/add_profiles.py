from onboarding.parsers.profiles import add_profiles
from services.management.base import BaseCommand
from ..utils import get_token_for_domain


class Command(BaseCommand):

    help = 'Add profiles for an organization'

    def add_arguments(self, parser):
        parser.add_argument('organization_domain', type=str, help='Organization\'s domain')
        parser.add_argument('filename', help='Filename with profile data we\'re adding')

    def handle(self, *args, **options):
        organization_domain = options['organization_domain']
        filename = options['filename']
        token = get_token_for_domain(organization_domain)
        add_profiles(filename, token)
