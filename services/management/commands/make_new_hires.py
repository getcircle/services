import arrow
from optparse import make_option
from services.management.base import BaseCommand

from organizations import models as organization_models
from profiles import models as profile_models


class Command(BaseCommand):
    help = 'One-off to create some new hires'
    args = '<organization domain>'
    option_list = BaseCommand.option_list + (
        make_option(
            '--count',
            action='store',
            dest='count',
            default=5,
            type='int',
            help='The number of new hires to create',
        ),
    )

    def handle(self, *args, **options):
        teams = organization_models.Team.objects.filter(organization__domain=args[0]).order_by(
            '-path'
        )[:5]
        profile_models.Profile.objects.filter(team_id__in=[team.pk for team in teams]).update(
            hire_date=arrow.now().replace(days=-1).date(),
        )
