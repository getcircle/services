from onboarding.parsers.skills import Parser

from .base import BaseOrganizationParserCommand


class Command(BaseOrganizationParserCommand):
    parser_class = Parser
