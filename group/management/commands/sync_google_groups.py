from protobufs.services.organization.containers import integration_pb2
import service.control

from group.providers.google import Provider
from group.providers.google.sync import Sync
from services.management.base import BaseCommand
from services.token import make_admin_token


class Command(BaseCommand):
    help = 'Sync groups for an organization'

    def add_arguments(self, parser):
        parser.add_argument('organization_domain', type=str, help='Organization\'s domain')

    def handle(self, *args, **options):
        client = service.control.Client('organization', token=make_admin_token())
        organization = client.get_object(
            'get_organization',
            return_object='organization',
            organization_domain=options['organization_domain'],
        )
        integration = client.get_object(
            'get_integration',
            return_object='integration',
            integration_type=integration_pb2.GOOGLE_GROUPS,
        )

        token = make_admin_token(organization_id=organization.id)
        provider = Provider(token=token, organization=organization, integration=integration)
        sync = Sync(provider)
        sync.sync_groups()
