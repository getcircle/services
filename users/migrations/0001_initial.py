# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import uuid


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(null=True, verbose_name='last login', blank=True)),
                ('id', models.UUIDField(default=uuid.uuid4, max_length=32, serialize=False, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('changed', models.DateTimeField(auto_now=True)),
                ('is_admin', models.BooleanField(default=False)),
                ('is_active', models.BooleanField(default=True)),
                ('primary_email', models.EmailField(unique=True, max_length=254)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
    ]
