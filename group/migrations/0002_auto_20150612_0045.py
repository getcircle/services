# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('group', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='googlegroup',
            name='last_sync_id',
            field=models.UUIDField(null=True),
        ),
        migrations.AlterField(
            model_name='googlegroupmember',
            name='last_sync_id',
            field=models.UUIDField(null=True),
        ),
    ]
