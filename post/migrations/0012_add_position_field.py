# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('post', '0011_auto_20160228_2330'),
    ]

    operations = [
        migrations.AddField(
            model_name='collection',
            name='position',
            field=models.PositiveSmallIntegerField(null=True),
        ),
        migrations.AlterUniqueTogether(
            name='collection',
            unique_together=set([('organization_id', 'owner_id', 'owner_type', 'is_default'), ('organization_id', 'owner_id', 'owner_type', 'position')]),
        ),
    ]
