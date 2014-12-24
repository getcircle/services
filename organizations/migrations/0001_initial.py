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
            name='Organization',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, max_length=32, serialize=False, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('changed', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=256)),
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
                ('name', models.CharField(max_length=256)),
                ('owner_id', models.UUIDField(max_length=32)),
                ('path', organizations.models.LTreeField(null=True)),
                ('organization', models.ForeignKey(to='organizations.Organization')),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='TeamMembership',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, max_length=32, serialize=False, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('changed', models.DateTimeField(auto_now=True)),
                ('user_id', models.UUIDField(max_length=32)),
                ('team', models.ForeignKey(to='organizations.Team')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='teammembership',
            unique_together=set([('team', 'user_id')]),
        ),
    ]
