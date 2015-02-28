# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import uuid


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Appreciation',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, max_length=32, serialize=False, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('changed', models.DateTimeField(auto_now=True)),
                ('source_profile_id', models.UUIDField(max_length=32)),
                ('destination_profile_id', models.UUIDField(max_length=32)),
                ('content', models.TextField()),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
