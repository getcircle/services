# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import protobufs.services.organization.containers.integration_pb2
import common.db.models.fields


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0036_auto_20151009_1818'),
    ]

    operations = [
        migrations.AddField(
            model_name='integration',
            name='provider_uid',
            field=models.CharField(max_length=255, unique=True, null=True),
        ),
        migrations.AlterField(
            model_name='integration',
            name='details',
            field=common.db.models.fields.ProtobufField(null=True, protobuf_classes=[protobufs.services.organization.containers.integration_pb2.GoogleGroupDetailsV1, protobufs.services.organization.containers.integration_pb2.SlackSlashCommandDetailsV1]),
        ),
        migrations.AlterField(
            model_name='integration',
            name='type',
            field=models.SmallIntegerField(choices=[(0, b'GOOGLE_GROUPS'), (1, b'SLACK_SLASH_COMMAND')]),
        ),
    ]
