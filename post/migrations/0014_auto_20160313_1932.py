# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging

from django.db import models, migrations

logger = logging.getLogger(__name__)


def ensure_item_position(apps, schema_editor):
    Collection = apps.get_model('post', 'Collection')
    CollectionItem = apps.get_model('post', 'CollectionItem')
    for collection in Collection.objects.all():
        items = CollectionItem.objects.filter(
            collection_id=collection.pk,
            organization_id=collection.organization_id,
        ).order_by('position')
        for index, item in enumerate(items):
            if item.position != index:
                logger.info(
                    'correcting item position: %s: %s -> %s',
                    item.pk,
                    item.position,
                    index,
                )
                item.position = index
                item.save()


class Migration(migrations.Migration):

    dependencies = [
        ('post', '0013_populate_position_values'),
    ]

    operations = [
        migrations.RunPython(ensure_item_position, reverse_code=migrations.RunPython.noop),
    ]
