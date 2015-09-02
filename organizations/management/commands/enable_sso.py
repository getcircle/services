import requests
from services.management.base import (
    BaseCommand,
    CommandError,
)

from ... import models
from authentication import utils


class Command(BaseCommand):
    help = 'Enables SSO for an organization'

    def add_arguments(self, parser):
        parser.add_argument('organization_domain', type=str, help='Organization\'s domain')
        parser.add_argument('metadata_url', type=str, help='SAML Metadata URL')
        parser.add_argument(
            '--override',
            action='store_true',
            help='If specified, we\'ll override existing metadata',
        )

    def handle(self, *args, **options):
        organization_domain = options['organization_domain']
        metadata_url = options['metadata_url']
        try:
            organization = models.Organization.objects.get(domain=organization_domain)
        except models.Organization.DoesNotExist:
            raise CommandError('Organization: "%s" doesn\'t exist')

        response = requests.get(metadata_url)
        if not response.ok:
            raise CommandError('Failed to fetch metadata: %s' % (response.reason,))

        metadata = response.content

        # verify the metadata contents
        try:
            utils.get_saml_config(organization_domain, metadata)
        except Exception as e:
            raise CommandError('Invalid metadata: %s' % (e,))

        sso, created = models.SSO.objects.get_or_create(
            organization=organization,
            defaults={
                'metadata_url': metadata_url,
                'metadata': metadata,
            },
        )
        if not created and options['override']:
            sso.metadata_url = metadata_url
            sso.metadata = metadata
            sso.save()
