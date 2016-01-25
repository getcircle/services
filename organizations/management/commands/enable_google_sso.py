from protobufs.services.organization.containers import sso_pb2
from services.management.base import (
    BaseCommand,
    CommandError,
)

from ... import models


class Command(BaseCommand):
    help = 'Enables SSO via Google for an organization'

    def add_arguments(self, parser):
        parser.add_argument('organization_domain', type=str, help='Organization\'s domain')
        parser.add_argument(
            'domain',
            type=str,
            nargs='+',
            help='Google domain that is allowed to authenticate to the organization',
        )
        parser.add_argument(
            '--overwrite',
            action='store_true',
            help='If specified, we\'ll overwrite existing SSO settings',
        )

    def handle(self, *args, **options):
        organization_domain = options['organization_domain']
        domains = options['domain']
        try:
            organization = models.Organization.objects.get(domain=organization_domain)
        except models.Organization.DoesNotExist:
            raise CommandError('Organization: "%s" doesn\'t exist' % (organization_domain,))

        details = sso_pb2.GoogleDetailsV1(domains=domains)
        sso, created = models.SSO.objects.get_or_create(
            organization=organization,
            defaults={
                'provider': sso_pb2.GOOGLE,
                'details': details,
            },
        )
        if not created and options['overwrite']:
            print 'overwriting existing SSO details'
            sso.details = details
            sso.save()
        elif created:
            print 'Google SSO details loaded for: %s' % (organization_domain,)
        else:
            print 'SSO details exist, run with `--overwrite` to overwrite.'
