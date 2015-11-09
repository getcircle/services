# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import protobufs.services.organization.containers.integration_pb2
import common.db.models.fields


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0037_auto_20151109_2036'),
    ]

    operations = [
        migrations.AlterField(
            model_name='integration',
            name='details',
            field=common.db.models.fields.ProtobufField(null=True, protobuf_classes=[protobufs.services.organization.containers.integration_pb2.GoogleGroupDetailsV1, protobufs.services.organization.containers.integration_pb2.SlackSlashCommandDetailsV1, protobufs.services.organization.containers.integration_pb2.SlackWebApiDetailsV1]),
        ),
        migrations.AlterField(
            model_name='integration',
            name='type',
            field=models.SmallIntegerField(choices=[(0, b'GOOGLE_GROUPS'), (1, b'SLACK_SLASH_COMMAND'), (2, b'SLACK_WEB_API')]),
        ),
    ]
