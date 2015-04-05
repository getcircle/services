from django.core.management.base import BaseCommand as DjangoBaseCommand
from django.core.management.base import CommandError  # NOQA

from ..bootstrap import Bootstrap


class BaseCommand(DjangoBaseCommand):

    def execute(self, *args, **kwargs):
        Bootstrap.bootstrap()
        super(BaseCommand, self).execute(*args, **kwargs)
