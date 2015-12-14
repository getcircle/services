from services.management.base import BaseCommand

from organizations.helpers import (
    create_mx_record_for_subdomain,
    create_ses_verification_record_for_subdomain,
)


class Command(BaseCommand):
    help = 'Enable email ingestion for the given organization.'

    def add_arguments(self, parser):
        parser.add_argument(
            'organization_domain',
            type=str,
            help='Organization\'s domain',
        )

    def handle(self, *args, **options):
        domain = options['organization_domain']
        create_mx_record_for_subdomain(domain)
        create_ses_verification_record_for_subdomain(domain)
