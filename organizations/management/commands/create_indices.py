import service.control

from organizations import models
from services.management.base import BaseCommand
from services.token import make_admin_token


class Command(BaseCommand):
    help = 'Create search indices for any organizations that don\'t currently have one.'

    def handle(self, *args, **options):
        organizations = models.Organization.objects.all()
        for organization in organizations:
            try:
                service.control.call_action(
                    service='search',
                    action='create_index',
                    client_kwargs={'token': make_admin_token(organization_id=str(organization.pk))},
                )
            except service.control.CallActionError:
                print 'index for %s already exists' % (organization.domain,)
            else:
                print '--> created index for %s' % (organization.domain,)
