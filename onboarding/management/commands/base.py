from optparse import make_option

from onboarding.parsers.exceptions import ParseError
from services.management.base import (
    BaseCommand,
    CommandError,
)


class BaseOrganizationParserCommand(BaseCommand):
    parser_class = None
    args = '<organization domain> <filename>'
    help = 'Loads the onboarding file into the organization'
    option_list = BaseCommand.option_list + (
        make_option(
            '--commit',
            action='store_true',
            dest='commit',
            default=False,
            help='Commit the parsed data',
        ),
        make_option(
            '--verbose',
            action='store_true',
            dest='verbose',
            default=False,
            help='Run the command with debug logging',
        ),
    )

    def handle(self, *args, **options):
        if self.parser_class is None:
            raise NotImplementedError('BaseOrganizationParserCommand must specify "parser_class"')

        organization_domain = args[0]
        filename = args[1]

        parser = self.parser_class(
            organization_domain=organization_domain,
            filename=filename,
            token='admin-token',
            verbose=options['verbose'],
        )
        try:
            parser.parse(commit=options['commit'])
        except ParseError as e:
            raise CommandError('Error parsing file: %s' % (e.args[0],))

