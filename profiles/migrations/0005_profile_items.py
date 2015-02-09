# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.contrib.postgres.fields


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0004_auto_20150206_2254'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='items',
            field=django.contrib.postgres.fields.ArrayField(null=True, base_field=django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=256, null=True), size=2), size=None),
        ),
    ]
