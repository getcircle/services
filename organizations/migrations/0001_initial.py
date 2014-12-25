# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from common.db.migrations.operations import LoadExtension
from django.db import models, migrations

import organizations.models
import uuid


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        LoadExtension('ltree'),
        migrations.CreateModel(
            name='Address',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, max_length=32, serialize=False, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('changed', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=64)),
                ('address_1', models.CharField(max_length=128)),
                ('address_2', models.CharField(max_length=128, blank=True)),
                ('city', models.CharField(max_length=64)),
                ('region', models.CharField(max_length=64)),
                ('postal_code', models.CharField(max_length=5)),
                ('country_code', models.CharField(max_length=2)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Organization',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, max_length=32, serialize=False, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('changed', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=64)),
                ('domain', models.CharField(unique=True, max_length=64)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Team',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, max_length=32, serialize=False, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('changed', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=64)),
                ('owner_id', models.UUIDField(max_length=32, db_index=True)),
                ('path', organizations.models.LTreeField(null=True)),
                ('organization', models.ForeignKey(to='organizations.Organization')),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='address',
            name='organization_id',
            field=models.ForeignKey(to='organizations.Organization'),
            preserve_default=True,
        ),
    ]
