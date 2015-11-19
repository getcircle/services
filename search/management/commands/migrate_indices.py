from services.management.base import BaseCommand

from ...actions.migrations import (
    get_indices_to_migrate,
    migrate_index,
)


class Command(BaseCommand):

    help = 'Migrate all organizations to the latest index version'

    def handle(self, *args, **options):
        indices = get_indices_to_migrate()
        for index in indices:
            migrate_index(index)
