# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import protobufs.services.post.containers_pb2
import uuid


class CollectionItemDeferredUniqueTogether(migrations.AlterUniqueTogether):

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        new_model = to_state.apps.get_model(app_label, self.name)
        if self.allow_migrate_model(schema_editor.connection.alias, new_model):
            statement = schema_editor._create_unique_sql(
                new_model,
                ('organization_id', 'collection_id', 'position'),
            )
            statement += ' INITIALLY DEFERRED'
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
        CollectionItemDeferredUniqueTogether(
            name='collectionitem',
            unique_together=set([('organization_id', 'collection', 'position')]),
        ),
        migrations.AlterIndexTogether(
            name='collectionitem',
            index_together=set([('organization_id', 'source', 'source_id')]),
        ),
    ]
