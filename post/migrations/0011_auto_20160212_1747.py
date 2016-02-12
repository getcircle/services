# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('post', '0010_auto_20160211_0141'),
    ]

    operations = [
        migrations.AlterField(
            model_name='collection',
            name='is_default',
            field=models.NullBooleanField(editable=False),
        ),
        migrations.AlterUniqueTogether(
            name='collection',
            unique_together=set([('organization_id', 'owner_id', 'owner_type', 'is_default')]),
        ),
        migrations.AlterIndexTogether(
            name='collection',
            index_together=set([('id', 'organization_id')]),
        ),
        migrations.AlterIndexTogether(
            name='collectionitem',
            index_together=set([('organization_id', 'source', 'source_id'), ('organization_id', 'collection', 'position')]),
        ),
    ]
