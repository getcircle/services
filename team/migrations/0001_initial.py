# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import protobufs.services.team.containers_pb2
import services.fields
import uuid


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Team',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, serialize=False, editable=False, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('changed', models.DateTimeField(auto_now=True)),
                ('organization_id', models.UUIDField(db_index=True)),
                ('name', models.CharField(max_length=255)),
                ('description', services.fields.DescriptionField(null=True)),
            ],
            options={
                'protobuf': protobufs.services.team.containers_pb2.TeamV1,
            },
        ),
        migrations.CreateModel(
            name='TeamMember',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, serialize=False, editable=False, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('changed', models.DateTimeField(auto_now=True)),
                ('profile_id', models.UUIDField()),
                ('organization_id', models.UUIDField()),
                ('role', models.SmallIntegerField(default=0, choices=[(0, b'MEMBER'), (1, b'COORDINATOR')])),
                ('team', models.ForeignKey(related_name='members', to='team.Team')),
            ],
            options={
                'protobuf': protobufs.services.team.containers_pb2.TeamMemberV1,
            },
        ),
        migrations.AlterIndexTogether(
            name='teammember',
            index_together=set([('profile_id', 'organization_id'), ('team', 'organization_id', 'role')]),
        ),
    ]
