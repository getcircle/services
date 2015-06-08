from protobuf_to_dict import protobuf_to_dict
from protobufs.services.organization.containers import integration_pb2
import service.control

from services.management.base import BaseCommand
from services.token import make_admin_token

from organizations import models as organization_models


class Command(BaseCommand):
    help = 'Enable the google groups integration for the given organization.'

    def add_arguments(self, parser):
        parser.add_argument(
            'organization_domain',
            type=str,
            help='Organization\'s domain',
        )
        parser.add_argument(
            'admin_email',
            type=str,
            help='Google Admin email account for the organization',
        )

    def handle(self, *args, **options):
        organization = organization_models.Organization.objects.get(
            domain=options['organization_domain'],
        )
        token = make_admin_token(organization_id=str(organization.id))
        client = service.control.Client('organization', token=token)
        response = client.call_action('enable_integration', integration={
            'integration_type': integration_pb2.GOOGLE_GROUPS,
            'google_groups': {'admin_email': options['admin_email']},
        })
        print protobuf_to_dict(response.result.integration)
