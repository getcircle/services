from onboarding.parsers.organizations import Parser

from .base import BaseOrganizationParserCommand


class Command(BaseOrganizationParserCommand):
    parser_class = Parser
