from optparse import make_option

import django.db
from services.management.base import BaseCommand

from organizations import models as organization_models
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

        queryset = organization_models.Team.objects.filter(organization_id=organization.id)
        if locked_users:
            print 'locking users: %s' % (
                ', '.join([locked_user.primary_email for locked_user in locked_users]),
            )
            queryset = queryset.exclude(
                owner_id__in=[locked_user.id for locked_user in locked_users]
            )

        # NB: Don't include the CEO
        teams = queryset.order_by('path')[1:len(emails) + 1]
        for index, email in enumerate(emails):
            print 'adding user: %s' % (email,)
            try:
                with django.db.transaction.atomic():
                    user_models.User.objects.filter(
                        id=teams[index].owner_id,
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
                user_models.User.objects.filter(id=teams[index].owner_id).update(
                    primary_email=email,
                )
