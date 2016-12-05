# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import protobufs.services.file.containers_pb2
import uuid


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='File',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, serialize=False, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('changed', models.DateTimeField(auto_now=True)),
                ('by_profile_id', models.UUIDField()),
                ('organization_id', models.UUIDField(db_index=True)),
                ('source_url', models.CharField(max_length=255)),
            ],
            options={
                'protobuf': protobufs.services.file.containers_pb2.FileV1,
            },
        ),
    ]
