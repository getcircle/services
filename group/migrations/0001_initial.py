# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from common.db.migrations.operations import LoadExtension
from django.db import models, migrations
import django.contrib.postgres.fields
import django.contrib.postgres.fields.hstore
import uuid


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        LoadExtension('hstore'),
        migrations.CreateModel(
            name='GoogleGroup',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, serialize=False, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('changed', models.DateTimeField(auto_now=True)),
                ('provider_uid', models.CharField(max_length=255)),
                ('email', models.CharField(max_length=255, db_index=True)),
                ('display_name', models.CharField(max_length=255, null=True)),
                ('name', models.CharField(max_length=255)),
                ('description', models.TextField(null=True)),
                ('direct_members_count', models.IntegerField(default=0)),
                ('aliases', django.contrib.postgres.fields.ArrayField(null=True, base_field=models.CharField(max_length=255), size=None)),
                ('settings', django.contrib.postgres.fields.hstore.HStoreField(null=True)),
                ('last_sync_id', models.UUIDField()),
                ('organization_id', models.UUIDField()),
            ],
        ),
        migrations.CreateModel(
            name='GoogleGroupMember',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('changed', models.DateTimeField(auto_now=True)),
                ('profile_id', models.UUIDField(db_index=True)),
                ('provider_uid', models.CharField(max_length=255)),
                ('role', models.CharField(max_length=255, db_index=True)),
                ('organization_id', models.UUIDField()),
                ('last_sync_id', models.UUIDField()),
                ('group', models.ForeignKey(to='group.GoogleGroup')),
            ],
        ),
        migrations.CreateModel(
            name='GroupMembershipRequest',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, serialize=False, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('changed', models.DateTimeField(auto_now=True)),
                ('status', models.SmallIntegerField(choices=[(0, b'PENDING'), (1, b'APPROVED'), (2, b'DENIED')])),
                ('requester_profile_id', models.UUIDField(db_index=True)),
                ('approver_profile_ids', django.contrib.postgres.fields.ArrayField(size=None, null=True, base_field=models.UUIDField(), db_index=True)),
                ('group_id', models.UUIDField()),
                ('provider', models.SmallIntegerField(choices=[(0, b'GOOGLE')])),
                ('meta', django.contrib.postgres.fields.hstore.HStoreField(null=True)),
            ],
        ),
        migrations.AlterIndexTogether(
            name='groupmembershiprequest',
            index_together=set([('provider', 'group_id')]),
        ),
        migrations.AlterUniqueTogether(
            name='googlegroup',
            unique_together=set([('provider_uid', 'organization_id')]),
        ),
        migrations.AlterIndexTogether(
            name='googlegroup',
            index_together=set([('last_sync_id', 'organization_id')]),
        ),
        migrations.AlterUniqueTogether(
            name='googlegroupmember',
            unique_together=set([('profile_id', 'group', 'organization_id')]),
        ),
        migrations.AlterIndexTogether(
            name='googlegroupmember',
            index_together=set([('profile_id', 'organization_id'), ('last_sync_id', 'organization_id'), ('group', 'organization_id')]),
        ),
    ]
