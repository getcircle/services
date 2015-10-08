import service.control

from onboarding.parsers.profiles import add_profiles
from services.management.base import BaseCommand
from services.token import make_admin_token


class Command(BaseCommand):

    help = 'Add profiles for an organization'

    def add_arguments(self, parser):
        parser.add_argument('organization_domain', type=str, help='Organization\'s domain')
        parser.add_argument('filename', help='Filename with profile data we\'re adding')

    def handle(self, *args, **options):
        organization_domain = options['organization_domain']
        filename = options['filename']
        client = service.control.Client('organization', token=make_admin_token())
        response = client.call_action('get_organization', domain=organization_domain)
        organization = response.result.organization
        token = make_admin_token(organization_id=organization.id)
        add_profiles(filename, token)
