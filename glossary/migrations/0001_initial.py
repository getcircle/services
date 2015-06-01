# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import protobufs.services.glossary.containers_pb2
import uuid


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Term',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, serialize=False, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('changed', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=255)),
                ('definition', models.TextField()),
                ('organization_id', models.UUIDField(db_index=True)),
                ('created_by_profile_id', models.UUIDField()),
            ],
            options={
                'protobuf': protobufs.services.glossary.containers_pb2.TermV1,
            },
        ),
        migrations.AlterUniqueTogether(
            name='term',
            unique_together=set([('name', 'organization_id')]),
        ),
    ]
