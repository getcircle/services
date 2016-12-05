from django.core.management.base import BaseCommand as DjangoBaseCommand
from django.core.management.base import CommandError  # NOQA
import service.control

from ..bootstrap import Bootstrap


class BaseCommand(DjangoBaseCommand):

    def execute(self, *args, **kwargs):
        Bootstrap.bootstrap()
        try:
            super(BaseCommand, self).execute(*args, **kwargs)
        except service.control.CallActionError as e:
            raise CommandError(e)
