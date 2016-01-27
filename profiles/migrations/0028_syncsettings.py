# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0027_profile_sync_source_id'),
    ]

    operations = [
        migrations.CreateModel(
            name='SyncSettings',
            fields=[
                ('created', models.DateTimeField(auto_now_add=True)),
                ('changed', models.DateTimeField(auto_now=True)),
                ('organization_id', models.UUIDField(serialize=False, primary_key=True)),
                ('mappings', models.TextField()),
                ('validate_fields', models.TextField(null=True)),
                ('endpoint', models.CharField(max_length=255)),
                ('api_key', models.CharField(max_length=255)),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
