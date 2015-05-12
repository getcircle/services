from optparse import make_option
import subprocess

from django.conf import settings
from django.db import connection
import service.control

from services.management.base import (
    BaseCommand,
    CommandError,
)
from services.token import make_admin_token


class Command(BaseCommand):
    args = '<organization name> <organization domain>'
    help = 'Creates an organization'
    option_list = BaseCommand.option_list + (
        make_option(
            '--image_url',
            dest='image_url',
            help='Link to the companies logo',
        ),
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
            verify = raw_input('are you sure you want to reset the db? ')
            if verify != 'yes':
                raise CommandError('Cancelling create with reset. Failed verification.')

            if not settings.DEBUG:
                double_check = raw_input(
                    'it looks like you\'re in production, proceed with reset? '
                )
                if double_check != 'yes':
                    raise CommandError('Cancelling create with reset. Failed double check.')

            cursor = connection.cursor()
            cursor.execute('DROP SCHEMA PUBLIC CASCADE')
            cursor.execute('CREATE SCHEMA PUBLIC')
            subprocess.call(['python', 'manage.py', 'migrate', '--noinput'])

        client = service.control.Client('organization', token=make_admin_token())
        organization = {
            'name': organization_name,
            'domain': organization_domain,
        }
        if 'image_url' in options:
            organization['image_url'] = options.get('image_url')

        response = client.call_action(
            'create_organization',
            organization=organization,
        )

        client = service.control.Client(
            'organization',
            token=make_admin_token(organization_id=response.result.organization.id),
        )
        client.call_action('create_token')
        if not response.success:
            raise CommandError('Error creating organization: %s' % (
                response.errors,
            ))

        print 'created organization "%s": %s' % (
            response.result.organization.name,
            response.result.organization.id,
        )
