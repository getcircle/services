# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0026_auto_20160120_1748'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='sync_source_id',
            field=models.CharField(max_length=255, null=True),
        ),
    ]
