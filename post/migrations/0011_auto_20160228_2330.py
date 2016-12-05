# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('post', '0010_auto_20160224_1406'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='collectionitem',
            unique_together=set([('organization_id', 'collection', 'source', 'source_id'), ('organization_id', 'collection', 'position')]),
        ),
    ]
