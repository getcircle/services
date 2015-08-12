# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.contrib.postgres.fields


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0012_auto_20150804_0301'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='profile',
            name='address_id',
        ),
        migrations.RemoveField(
            model_name='profile',
            name='location_id',
        ),
        migrations.RemoveField(
            model_name='profile',
            name='tags',
        ),
        migrations.RemoveField(
            model_name='profile',
            name='team_id',
        ),
        migrations.AlterField(
            model_name='profile',
            name='image_url',
            field=models.URLField(max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='profile',
            name='items',
            field=django.contrib.postgres.fields.ArrayField(null=True, base_field=django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=255, null=True), size=2), size=None),
        ),
        migrations.AlterField(
            model_name='profile',
            name='small_image_url',
            field=models.URLField(max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='profile',
            name='title',
            field=models.CharField(max_length=255, null=True),
        ),
    ]
