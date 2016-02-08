# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import protobufs.services.team.containers_pb2
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('team', '0003_auto_20160201_0544'),
    ]

    operations = [
        migrations.CreateModel(
            name='ContactMethod',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, serialize=False, editable=False, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('changed', models.DateTimeField(auto_now=True)),
                ('label', models.CharField(max_length=64)),
                ('value', models.CharField(max_length=64)),
                ('type', models.SmallIntegerField(default=0, choices=[(0, b'EMAIL'), (1, b'SLACK')])),
                ('organization_id', models.UUIDField()),
                ('team', models.ForeignKey(related_name='contact_methods', to='team.Team')),
            ],
            options={
                'protobuf': protobufs.services.team.containers_pb2.ContactMethodV1,
            },
        ),
        migrations.AlterIndexTogether(
            name='contactmethod',
            index_together=set([('team', 'organization_id')]),
        ),
    ]
