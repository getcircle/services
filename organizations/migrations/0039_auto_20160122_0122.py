# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import common.db.models.fields
import protobufs.services.organization.containers.sso_pb2


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0038_auto_20160121_0001'),
    ]

    operations = [
        migrations.AddField(
            model_name='sso',
            name='details',
            field=common.db.models.fields.ProtobufField(null=True, protobuf_classes=[protobufs.services.organization.containers.sso_pb2.SAMLDetailsV1, protobufs.services.organization.containers.sso_pb2.GoogleDetailsV1]),
        ),
        migrations.AlterField(
            model_name='sso',
            name='provider',
            field=models.SmallIntegerField(choices=[(0, b'OKTA'), (1, b'GOOGLE')]),
        ),
    ]
