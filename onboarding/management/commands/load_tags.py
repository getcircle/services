from onboarding.parsers.tags import Parser

from .base import BaseOrganizationParserCommand


class Command(BaseOrganizationParserCommand):
    parser_class = Parser
