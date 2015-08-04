# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import protobufs.services.organization.containers_pb2
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0020_location_established_date'),
    ]

    operations = [
        migrations.CreateModel(
            name='TeamStatus',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, serialize=False, primary_key=True)),
                ('value', models.TextField(null=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('organization_id', models.UUIDField()),
                ('by_profile_id', models.UUIDField()),
                ('team', models.ForeignKey(to='organizations.Team')),
            ],
            options={
                'protobuf': protobufs.services.organization.containers_pb2.TeamStatusV1,
            },
        ),
        migrations.AlterIndexTogether(
            name='teamstatus',
            index_together=set([('team', 'organization_id', 'created')]),
        ),
    ]
