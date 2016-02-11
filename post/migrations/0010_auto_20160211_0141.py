# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('post', '0009_auto_20160210_2039'),
    ]

    operations = [
        migrations.AlterField(
            model_name='collection',
            name='by_profile_id',
            field=models.UUIDField(null=True, editable=False),
        ),
        migrations.AlterField(
            model_name='collection',
            name='is_default',
            field=models.BooleanField(default=False, editable=False),
        ),
        migrations.AlterField(
            model_name='collection',
            name='organization_id',
            field=models.UUIDField(editable=False),
        ),
        migrations.AlterUniqueTogether(
            name='collectionitem',
            unique_together=set([]),
        ),
    ]
