from onboarding.parsers.organizations import ParserV2

from .base import BaseOrganizationParserCommand


class Command(BaseOrganizationParserCommand):
    parser_class = ParserV2
