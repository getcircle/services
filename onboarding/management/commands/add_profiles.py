from onboarding.parsers.profiles import add_profiles
from services.management.base import BaseCommand
from services.token import get_token_for_domain


class Command(BaseCommand):

    help = 'Add profiles for an organization'

    def add_arguments(self, parser):
        parser.add_argument('organization_domain', type=str, help='Organization\'s domain')
        parser.add_argument('filename', help='Filename with profile data we\'re adding')
        parser.add_argument('--id_field_name', help='Field name of unique profile identifier')
        parser.add_argument(
            '--manager_id_field_name',
            help='Field name of unique manager identifier',
        )

    def handle(self, *args, **options):
        organization_domain = options['organization_domain']
        filename = options['filename']
        token = get_token_for_domain(organization_domain)
        add_profiles(
            filename,
            token,
            id_field_name=options.get('id_field_name'),
            manager_id_field_name=options.get('manager_id_field_name'),
        )
