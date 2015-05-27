from protobuf_to_dict import protobuf_to_dict
from protobufs.services.organization.containers import integration_pb2
import service.control

from services.management.base import BaseCommand
from services.token import make_admin_token

from organizations import models as organization_models


class Command(BaseCommand):
    help = 'One-off to add skills to profiles in an organization'
    args = '<organization_domain> <admin_email>'

    def handle(self, *args, **options):
        organization = organization_models.Organization.objects.get(domain=args[0])
        token = make_admin_token(organization_id=str(organization.id))
        client = service.control.Client('organization', token=token)
        response = client.call_action('enable_integration', integration={
            'integration_type': integration_pb2.GOOGLE_GROUPS,
            'google_groups': {'admin_email': args[1]},
        })
        print protobuf_to_dict(response.result.integration)
