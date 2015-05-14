# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from common.db.migrations.operations import LoadExtension
from django.db import models, migrations
import django.contrib.postgres.fields.hstore
import uuid


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        LoadExtension('hstore'),
        migrations.CreateModel(
            name='GroupMembershipRequest',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, serialize=False, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('changed', models.DateTimeField(auto_now=True)),
                ('status', models.SmallIntegerField(choices=[(0, b'PENDING'), (1, b'APPROVED'), (2, b'REJECTED')])),
                ('requester_profile_id', models.UUIDField()),
                ('approver_profile_id', models.UUIDField()),
                ('group_key', models.CharField(max_length=255)),
                ('provider', models.SmallIntegerField(choices=[(0, b'GOOGLE')])),
                ('meta', django.contrib.postgres.fields.hstore.HStoreField()),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
