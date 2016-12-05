# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('history', '0005_auto_20150813_0630'),
    ]

    operations = [
        migrations.AlterField(
            model_name='action',
            name='action_type',
            field=models.SmallIntegerField(null=True, choices=[(0, b'UPDATE_DESCRIPTION')]),
        ),
        migrations.AlterField(
            model_name='action',
            name='column_name',
            field=models.CharField(max_length=64, null=True),
        ),
        migrations.AlterField(
            model_name='action',
            name='data_type',
            field=models.CharField(max_length=32, null=True),
        ),
        migrations.AlterField(
            model_name='action',
            name='id',
            field=models.UUIDField(default=uuid.uuid4, serialize=False, editable=False, primary_key=True),
        ),
    ]
