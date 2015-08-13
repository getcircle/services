# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('history', '0004_action_table_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='action',
            name='primary_key_name',
            field=models.CharField(default='', max_length=64),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='action',
            name='primary_key_value',
            field=models.CharField(default='', max_length=255),
            preserve_default=False,
        ),
    ]
