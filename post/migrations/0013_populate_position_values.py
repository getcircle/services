# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


def gen_position(apps, schema_editor):
    Collection = apps.get_model('post', 'Collection')
    owners = Collection.objects.order_by().values_list('organization_id', 'owner_id', 'owner_type').distinct()
    for owner_info in owners:
        owner_collections = Collection.objects.filter(
            organization_id=owner_info[0],
            owner_id=owner_info[1],
            owner_type=owner_info[2],
        ).order_by('-created')
        for idx, collection in enumerate(owner_collections):
            collection.position = idx
            collection.save()

class Migration(migrations.Migration):

    dependencies = [
        ('post', '0012_add_position_field'),
    ]

    operations = [
        migrations.RunPython(gen_position, reverse_code=migrations.RunPython.noop),
    ]
