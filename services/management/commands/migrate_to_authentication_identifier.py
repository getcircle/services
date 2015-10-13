from csv import DictReader

from organizations.models import Organization
from profiles.models import Profile
from protobufs.services.user import containers_pb2 as user_containers
from services.management.base import BaseCommand
from users.models import Identity


class Command(BaseCommand):

    help = (
        'Update the authentication_identifiers for the given profiles.'
        ' A part of the migration to include authentication_identifier in profiles.'
    )

    def add_arguments(self, parser):
        parser.add_argument('organization_domain', type=str, help='Organization\'s domain')
        parser.add_argument('filename', help='Filename with profile data we\'re updating')
        parser.add_argument('--commit', action='store_true', help='Commit the changes to the db')

    def handle(self, *args, **options):
        organization = Organization.objects.get(domain=options['organization_domain'])
        filename = options['filename']
        with open(filename, 'rU') as read_file:
            reader = DictReader(read_file)
            for row_data in reader:
                profile_id = row_data['profile_id'].strip()
                employee_id = row_data['RV_EID'].strip()
                if not profile_id:
                    continue

                try:
                    profile = Profile.objects.get(
                        pk=row_data['profile_id'],
                        organization_id=organization.id,
                    )
                except Profile.DoesNotExist:
                    print 'profile not found for: %s' % (row_data,)
                    continue

                if employee_id and profile.authentication_identifier != employee_id:
                    profile.authentication_identifier = employee_id
                    print 'adding authentication_identifier: %s to profile: %s' % (
                        employee_id,
                        profile.email,
                    )
                    if options['commit']:
                        profile.save()

                    identity = Identity.objects.get(
                        user_id=profile.user_id,
                        provider=user_containers.IdentityV1.OKTA,
                    )
                    if identity.provider_uid != employee_id:
                        print 'updating provider_uid for identity: %s (%s)' % (
                            identity.email,
                            identity.pk,
                        )
                        if options['commit']:
                            identity.save()

                elif employee_id:
                    print 'authentication_identifier: %s already present for profile: %s' % (
                        employee_id,
                        profile.email,
                    )
                else:
                    print 'authentication_identifier not found in: %s' % (row_data,)
