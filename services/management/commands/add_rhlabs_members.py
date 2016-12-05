from optparse import make_option

import django.db
from services.management.base import BaseCommand

from organizations import models as organization_models
from profiles import models as profile_models
from services.test import fuzzy
from users import models as user_models


class Command(BaseCommand):
    help = 'One-off to add rhlabs members to an organization'
    args = '<organization_domain> <emails>'
    option_list = BaseCommand.option_list + (
        make_option(
            '--lock',
            action='append',
            dest='lock',
            help='An email address we want to make sure we\'re not overriding',
        ),
    )

    def handle(self, *args, **options):
        organization = organization_models.Organization.objects.get(domain=args[0])
        emails = args[1:]
        locked_users = options.get('lock')
        if locked_users:
            locked_users = user_models.User.objects.filter(primary_email__in=locked_users)
            locked_profiles = profile_models.Profile.objects.filter(
                user_id__in=[u.pk for u in locked_users],
            )

        queryset = organization_models.ReportingStructure.objects.filter(
            organization_id=organization.id,
        )
        if locked_users:
            print 'locking users: %s' % (
                ', '.join([locked_user.primary_email for locked_user in locked_users]),
            )
            queryset = queryset.exclude(
                profile_id__in=[locked_profile.id for locked_profile in locked_profiles]
            )

        # NB: Don't include the CEO
        managers = queryset.order_by('level')[1:len(emails) + 1]
        for index, email in enumerate(emails):
            print 'adding user: %s' % (email,)
            profile = profile_models.Profile.objects.get(pk=managers[index].profile_id)
            try:
                with django.db.transaction.atomic():
                    user_models.User.objects.filter(
                        id=profile.user_id,
                    ).update(primary_email=email)
            except django.db.IntegrityError:
                email_parts = email.split('@')
                new_email = '%s+%s@%s' % (
                    email_parts[0],
                    fuzzy.FuzzyText().fuzz(),
                    email_parts[1],
                )
                print 'user already exists, altering old user to: %s' % (new_email,)
                user_models.User.objects.filter(primary_email=email).update(
                    primary_email=new_email,
                )
                user_models.User.objects.filter(
                    id=profile.user_id,
                ).update(primary_email=email)
