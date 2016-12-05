# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import common.db.models.fields
import protobufs.services.organization.containers.sso_pb2


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0041_auto_20160122_1705'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sso',
            name='details',
            field=common.db.models.fields.ProtobufField(protobuf_classes=[protobufs.services.organization.containers.sso_pb2.SAMLDetailsV1, protobufs.services.organization.containers.sso_pb2.GoogleDetailsV1]),
        ),
    ]
