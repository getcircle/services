import service.control

from services.management.base import BaseCommand
from services.token import make_admin_token


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
        client = service.control.Client('organization', token=make_admin_token())
        response = client.call_action('get_organization', domain=organization_domain)
        organization = response.result.organization
        token = make_admin_token(organization_id=organization.id)
