from optparse import make_option

from onboarding.parsers.tags import Parser
from protobufs.services.profile import containers_pb2 as profile_containers
from services.management.base import CommandError

from .base import BaseOrganizationParserCommand


class Command(BaseOrganizationParserCommand):
    parser_class = Parser

    option_list = BaseOrganizationParserCommand.option_list + (
        make_option(
            '--tag_type',
            dest='tag_type',
            default='skill',
            help='Tag type to upload',
        ),
    )

    def handle(self, *args, **options):
        try:
            tag_type = getattr(profile_containers.TagV1, options['tag_type'].upper())
        except AttributeError:
            raise CommandError('Invalid tag type: %s' % (options['tag_type'],))
        self.parser_kwargs['tag_type'] = tag_type
        return super(Command, self).handle(*args, **options)
