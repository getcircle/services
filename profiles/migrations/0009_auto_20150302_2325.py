# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0008_auto_20150302_2305'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profile',
            name='address_id',
            field=models.UUIDField(max_length=32, null=True, db_index=True),
        ),
        migrations.AlterField(
            model_name='profile',
            name='location_id',
            field=models.UUIDField(max_length=32, null=True, db_index=True),
        ),
        migrations.AlterField(
            model_name='profile',
            name='team_id',
            field=models.UUIDField(max_length=32, db_index=True),
        ),
    ]
