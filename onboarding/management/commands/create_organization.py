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
    help = 'Creates an organization'

    def add_arguments(self, parser):
        parser.add_argument('organization_name', type=str, help='Organization\'s name')
        parser.add_argument('organization_domain', type=str, help='Organization\'s domain')
        parser.add_argument(
            '--image_url',
            dest='image_url',
            type=str,
            help='Link to the companies logo',
            required=False,
        )
        parser.add_argument(
            '--reset',
            action='store_true',
            required=False,
            default=False,
            help='Boolean for whether or not we should reset the schema before creating the org',
        )

    def handle(self, *args, **options):
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
            'name': options['organization_name'],
            'domain': options['organization_domain'],
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
