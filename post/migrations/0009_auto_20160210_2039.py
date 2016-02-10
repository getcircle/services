# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import protobufs.services.post.containers_pb2
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('post', '0008_auto_20160201_0456'),
    ]

    operations = [
        migrations.CreateModel(
            name='Collection',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, serialize=False, editable=False, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('changed', models.DateTimeField(auto_now=True)),
                ('organization_id', models.UUIDField()),
                ('owner_id', models.UUIDField()),
                ('owner_type', models.SmallIntegerField(default=0, choices=[(0, b'PROFILE'), (1, b'TEAM')])),
                ('name', models.CharField(max_length=64)),
                ('is_default', models.BooleanField(default=False)),
                ('by_profile_id', models.UUIDField(null=True)),
            ],
            options={
                'protobuf': protobufs.services.post.containers_pb2.CollectionV1,
            },
        ),
        migrations.CreateModel(
            name='CollectionItem',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, serialize=False, editable=False, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('changed', models.DateTimeField(auto_now=True)),
                ('position', models.PositiveSmallIntegerField()),
                ('by_profile_id', models.UUIDField(null=True)),
                ('organization_id', models.UUIDField()),
                ('source', models.SmallIntegerField(default=0, choices=[(0, b'LUNO')])),
                ('source_id', models.CharField(max_length=128)),
                ('collection', models.ForeignKey(to='post.Collection')),
            ],
            options={
                'protobuf': protobufs.services.post.containers_pb2.CollectionItemV1,
            },
        ),
        migrations.AlterIndexTogether(
            name='collection',
            index_together=set([('organization_id', 'owner_id', 'owner_type', 'is_default')]),
        ),
        migrations.AlterUniqueTogether(
            name='collectionitem',
            unique_together=set([('collection', 'position')]),
        ),
    ]
