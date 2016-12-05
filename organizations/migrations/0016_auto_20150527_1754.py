# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import protobufs.services.organization.containers.integration_pb2
import common.db.models.fields
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0015_auto_20150511_0317'),
    ]

    operations = [
        migrations.CreateModel(
            name='Integration',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, serialize=False, primary_key=True)),
                ('type', models.SmallIntegerField(choices=[(0, b'GOOGLE_GROUPS')])),
                ('details', common.db.models.fields.ProtobufField(null=True, protobuf_classes=[])),
                ('organization', models.ForeignKey(to='organizations.Organization')),
            ],
            options={
                'protobuf': protobufs.services.organization.containers.integration_pb2.IntegrationV1,
            },
        ),
        migrations.AlterUniqueTogether(
            name='integration',
            unique_together=set([('organization', 'type')]),
        ),
    ]
