from optparse import make_option
import subprocess

from django.db import connection
import service.control

from services.management.base import (
    BaseCommand,
    CommandError,
)


class Command(BaseCommand):
    args = '<organization name> <organization domain>'
    help = 'Creates an organization'
    option_list = BaseCommand.option_list + (
        make_option(
            '--reset',
            action='store_true',
            dest='reset',
            default=False,
            help='Boolean for whether or not we should reset the schema before creating the org',
        ),
    )

    def handle(self, *args, **options):
        organization_name = args[0]
        organization_domain = args[1]

        reset = options.get('reset')
        if reset:
            cursor = connection.cursor()
            cursor.execute('DROP SCHEMA PUBLIC CASCADE')
            cursor.execute('CREATE SCHEMA PUBLIC')
            subprocess.call(['python', 'manage.py', 'migrate', '--noinput'])

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
