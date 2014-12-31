import service.control

from services.management.base import (
    BaseCommand,
    CommandError,
)


class Command(BaseCommand):
    args = '<organization name> <organization domain>'
    help = 'Creates an organization'

    def handle(self, *args, **options):
        organization_name = args[0]
        organization_domain = args[1]

        # XXX we shouldn't have an admin token, we should have some way of
        # generating one on the fly though
        client = service.control.Client('organization', token='admin-token')
        response = client.call_action(
            'create_organization',
            organization={
                'name': organization_name,
                'domain': organization_domain,
            },
        )
        if not response.success:
            raise CommandError('Error creating organization: %s' % (
                response.errors,
            ))

        print 'created organization "%s": %s' % (
            response.result.organization.name,
            response.result.organization.id,
        )
