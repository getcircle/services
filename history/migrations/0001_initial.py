# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import protobufs.services.history.containers_pb2
import uuid


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Action',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, serialize=False, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('changed', models.DateTimeField(auto_now=True)),
                ('column_name', models.CharField(max_length=64)),
                ('data_type', models.CharField(max_length=32)),
                ('old_value', models.TextField()),
                ('new_value', models.TextField()),
                ('action_type', models.SmallIntegerField(choices=[(0, b'UPDATE_DESCRIPTION')])),
                ('method_type', models.SmallIntegerField(choices=[(0, b'UPDATE'), (1, b'DELETE')])),
                ('organization_id', models.UUIDField(db_index=True)),
                ('correlation_id', models.UUIDField()),
                ('by_profile_id', models.UUIDField()),
            ],
            options={
                'protobuf': protobufs.services.history.containers_pb2.ActionV1,
            },
        ),
    ]
