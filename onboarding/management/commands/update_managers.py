from onboarding.parsers.profiles import update_managers
from services.management.base import BaseCommand
from ..utils import get_token_for_domain


class Command(BaseCommand):

    help = 'Update the managers for the given profiles'

    def add_arguments(self, parser):
        parser.add_argument('organization_domain', type=str, help='Organization\'s domain')
        parser.add_argument(
            'filename',
            help='Filename with fields "email", "manager_email" we\'re updating',
        )

    def handle(self, *args, **options):
        organization_domain = options['organization_domain']
        filename = options['filename']
        token = get_token_for_domain(organization_domain)
        update_managers(filename, token)
