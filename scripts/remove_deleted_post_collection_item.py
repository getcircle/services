"""Script to delete any collection items whose posts have been deleted.

"""
import logging

from post.models import CollectionItem
from services.bootstrap import Bootstrap

logger = logging.getLogger(__name__)


def run():
    Bootstrap.bootstrap()
    orphaned_items = list(CollectionItem.objects.raw(
        """
            SELECT ci.*
            FROM post_collectionitem AS ci
                LEFT JOIN post_post AS p ON (ci.source_id::uuid = p.id and ci.source = 0)
            WHERE p.id is null
        """
    ))
    logger.info('deleting: %d orphaned items', len(orphaned_items))
    delete_confirmation = raw_input('delete these items? ')
    if delete_confirmation != 'yes!':
        logger.info('not deleting items.')
    else:
        logger.info('deleting items')
        items = CollectionItem.objects.filter(id__in=[item.pk for item in orphaned_items])
        for item in items:
            logger.info('deleting item: %s', item.as_dict())
        items.delete()
