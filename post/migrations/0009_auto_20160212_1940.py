# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import protobufs.services.post.containers_pb2
import uuid


def collection_item_unique_together_forwards(apps, schema_editor):
    CollectionItem = apps.get_model('post.CollectionItem')
    statement = schema_editor._create_unique_sql(
        CollectionItem,
        ('organization_id', 'collection_id', 'position'),
    )
    statement += ' INITIALLY DEFERRED'
    schema_editor.execute(statement)


def collection_item_unique_together_backwards(apps, schema_editor):
    CollectionItem = apps.get_model('post.CollectionItem')
    index_name = schema_editor._create_index_name(
        CollectionItem,
        ('organization_id', 'collection_id', 'position'),
        suffix='_uniq',
    )
    statement = schema_editor.sql_delete_unique % {
        'table': CollectionItem._meta.db_table,
        'name': index_name,
    }
    schema_editor.execute(statement)


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
                ('organization_id', models.UUIDField(editable=False)),
                ('owner_id', models.UUIDField()),
                ('owner_type', models.SmallIntegerField(default=0, choices=[(0, b'PROFILE'), (1, b'TEAM')])),
                ('name', models.CharField(max_length=64)),
                ('is_default', models.NullBooleanField(editable=False)),
                ('by_profile_id', models.UUIDField(null=True, editable=False)),
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
        migrations.AlterUniqueTogether(
            name='collection',
            unique_together=set([('organization_id', 'owner_id', 'owner_type', 'is_default')]),
        ),
        migrations.AlterIndexTogether(
            name='collection',
            index_together=set([('id', 'organization_id')]),
        ),
        migrations.RunPython(
            collection_item_unique_together_forwards,
            reverse_code=collection_item_unique_together_backwards,
        ),
        migrations.AlterIndexTogether(
            name='collectionitem',
            index_together=set([('organization_id', 'source', 'source_id')]),
        ),
    ]
