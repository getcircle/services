# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings
import pyotp
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_user_phone_number'),
    ]

    operations = [
        migrations.CreateModel(
            name='TOTPToken',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, max_length=32, serialize=False, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('changed', models.DateTimeField(auto_now=True)),
                ('token', models.CharField(default=pyotp.random_base32, max_length=16)),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
    ]
