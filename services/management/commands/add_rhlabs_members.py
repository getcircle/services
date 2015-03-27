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
            '--prevent',
            dest='prevent',
            help='An email address we want to make sure we\'re not overriding',
        ),
    )

    def handle(self, *args, **options):
        organization = organization_models.Organization.objects.get(domain=args[0])
        emails = args[1:]
        prevent_user = options.get('prevent')
        if prevent_user:
            prevent_user = user_models.User.objects.get(primary_email=options['prevent'])

        queryset = organization_models.Team.objects.filter(organization_id=organization.id)
        if prevent_user:
            print 'preventing user: %s' % (prevent_user.email,)
            queryset = queryset.exclude(owner_id=prevent_user.id)

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
