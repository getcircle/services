# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from common.db.migrations.operations import LoadExtension
from django.db import models, migrations
import django.contrib.postgres.fields.hstore
import phonenumber_field.modelfields
import uuid


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        LoadExtension('hstore'),
        migrations.CreateModel(
            name='Profile',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, max_length=32, serialize=False, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('changed', models.DateTimeField(auto_now=True)),
                ('organization_id', models.UUIDField(max_length=32)),
                ('user_id', models.UUIDField(max_length=32)),
                ('address_id', models.UUIDField(max_length=32)),
                ('team_id', models.UUIDField(max_length=32)),
                ('title', models.CharField(max_length=64)),
                ('first_name', models.CharField(max_length=64)),
                ('last_name', models.CharField(max_length=64)),
                ('cell_phone', phonenumber_field.modelfields.PhoneNumberField(max_length=128, null=True)),
                ('work_phone', phonenumber_field.modelfields.PhoneNumberField(max_length=128, null=True)),
                ('image_url', models.CharField(max_length=256, null=True)),
                ('location', django.contrib.postgres.fields.hstore.HStoreField(null=True)),
                ('email', models.EmailField(max_length=254)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='profile',
            unique_together=set([('organization_id', 'user_id')]),
        ),
    ]
