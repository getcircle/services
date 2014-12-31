from optparse import make_option

from onboarding.parsers import (
    ParseError,
    Parser,
)
from services.management.base import (
    BaseCommand,
    CommandError,
)


class Command(BaseCommand):
    args = '<organization domain> <filename>'
    help = 'Loads the onboarding file into the organization'
    option_list = BaseCommand.option_list + (
        make_option('--commit',
            action='store_true',
            dest='commit',
            default=False,
            help='Commit the parsed data'),
        )

    def handle(self, *args, **options):
        organization_domain = args[0]
        filename = args[1]

        parser = Parser(organization_domain, filename, 'admin-token')
        try:
            parser.parse(commit=options['commit'])
        except ParseError as e:
            raise CommandError('Error parsing file: %s' % (e.args[0],))
