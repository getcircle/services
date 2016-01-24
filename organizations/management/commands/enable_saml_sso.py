from protobufs.services.organization.containers import sso_pb2
import requests
from services.management.base import (
    BaseCommand,
    CommandError,
)

from ... import models
from users.authentication import utils


class Command(BaseCommand):
    help = 'Enables SSO for an organization'

    def add_arguments(self, parser):
        parser.add_argument('organization_domain', type=str, help='Organization\'s domain')
        parser.add_argument('metadata_url', type=str, help='SAML Metadata URL')
        parser.add_argument(
            '--overwrite',
            action='store_true',
            help='If specified, we\'ll overwrite existing SSO settings',
        )

    def handle(self, *args, **options):
        organization_domain = options['organization_domain']
        metadata_url = options['metadata_url']
        try:
            organization = models.Organization.objects.get(domain=organization_domain)
        except models.Organization.DoesNotExist:
            raise CommandError('Organization: "%s" doesn\'t exist' % (organization_domain,))

        response = requests.get(metadata_url)
        if not response.ok:
            raise CommandError('Failed to fetch metadata: %s' % (response.reason,))

        metadata = response.content

        # verify the metadata contents
        try:
            utils.get_saml_config(organization_domain, metadata)
        except Exception as e:
            raise CommandError('Invalid metadata: %s' % (e,))

        details = sso_pb2.SAMLDetailsV1(metadata_url=metadata_url, metadata=metadata)
        sso, created = models.SSO.objects.get_or_create(
            organization=organization,
            defaults={
                'provider': sso_pb2.OKTA,
                'details': details,
            },
        )
        if not created and options['overwrite']:
            print 'overwriting existing SSO details'
            sso.details = details
            sso.save()
        elif created:
            print 'SAML SSO details loaded for: %s' % (organization_domain,)
        else:
            print 'SAML SSO details exist, run with `--overwrite` to overwrite.'
