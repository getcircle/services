import os

from onboarding.parsers.exceptions import ParseError
from services.management.base import (
    BaseCommand,
    CommandError,
)
from services.token import make_admin_token


class BaseOrganizationParserCommand(BaseCommand):
    parser_class = None
    parser_kwargs = None
    help = 'Loads the onboarding file into the organization'

    def __init__(self, *args, **kwargs):
        if self.parser_kwargs is None:
            self.parser_kwargs = {}
        super(BaseOrganizationParserCommand, self).__init__(*args, **kwargs)

    def add_arguments(self, parser):
        parser.add_argument('organization_domain', type=str, help='Organization\'s domain')
        parser.add_argument(
            '--commit',
            action='store_true',
            help='Commit the parsed data',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Run the command with debug logging',
        )
        parser.add_argument(
            '--filename',
            help='Filename to load if it isn\'t the companies name',
        )
        parser.add_argument(
            '--locations-filename',
            help='Filename with locations to load',
        )

    def handle(self, *args, **options):
        if self.parser_class is None:
            raise NotImplementedError('BaseOrganizationParserCommand must specify "parser_class"')

        organization_domain = options['organization_domain']
        filename = options.get('filename')
        if not filename:
            filename = os.path.join(
                'onboarding',
                'fixtures',
                '%s_employee_import.csv' % (organization_domain.split('.')[0],),
            )

        #locations_filename = options.get('locations_filename')
        #if not locations_filename:
            #locations_filename = os.path.join(
                #'onboarding',
                #'fixtures',
                #'%s_office_import.csv' % (organization_domain.split('.')[0],),
            #)

        parser = self.parser_class(
            organization_domain=organization_domain,
            filename=filename,
            #locations_filename=locations_filename,
            token=make_admin_token(),
            verbose=options['verbose'],
        )
        try:
            parser.parse(commit=options['commit'], **self.parser_kwargs)
        except ParseError as e:
            raise CommandError('Error parsing file: %s' % (e.args[0],))
