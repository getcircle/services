# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import uuid


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='SyncJournal',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, serialize=False, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('changed', models.DateTimeField(auto_now=True)),
                ('journal_type', models.SmallIntegerField(db_index=True, choices=[(b'SyncCompleted', 0), (b'RecordProcessed', 1)])),
            ],
        ),
        migrations.CreateModel(
            name='SyncRecord',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, serialize=False, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('changed', models.DateTimeField(auto_now=True)),
                ('payload', models.TextField()),
                ('payload_type', models.SmallIntegerField(db_index=True, choices=[(0, b'USERS'), (1, b'GROUPS')])),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='SyncRequest',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, serialize=False, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('changed', models.DateTimeField(auto_now=True)),
                ('organization_id', models.UUIDField(db_index=True)),
                ('source', models.SmallIntegerField(db_index=True, choices=[(0, b'LDAP')])),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='syncrecord',
            name='sync',
            field=models.ForeignKey(to='sync.SyncRequest'),
        ),
        migrations.AddField(
            model_name='syncjournal',
            name='record',
            field=models.ForeignKey(to='sync.SyncRecord', null=True),
        ),
        migrations.AddField(
            model_name='syncjournal',
            name='sync',
            field=models.ForeignKey(to='sync.SyncRequest'),
        ),
        migrations.AlterUniqueTogether(
            name='syncjournal',
            unique_together=set([('sync', 'journal_type', 'record')]),
        ),
    ]
