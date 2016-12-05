from services.management.base import BaseCommand
from watson.management.commands.buildwatson import Command as WatsonCommand


class Command(BaseCommand, WatsonCommand):
    """Ensure Bootstrap is run before running watson command"""
