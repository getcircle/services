# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('appreciation', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='appreciation',
            name='destination_profile_id',
            field=models.UUIDField(max_length=32, db_index=True),
        ),
        migrations.AlterField(
            model_name='appreciation',
            name='source_profile_id',
            field=models.UUIDField(max_length=32, db_index=True),
        ),
    ]
