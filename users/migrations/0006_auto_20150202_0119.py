# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0005_user_phone_number_verified'),
    ]

    operations = [
        migrations.CreateModel(
            name='Identity',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, max_length=32, serialize=False, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('changed', models.DateTimeField(auto_now=True)),
                ('provider', models.PositiveSmallIntegerField(choices=[(1, b'LinkedIn')])),
                ('name', models.CharField(max_length=255)),
                ('email', models.EmailField(max_length=254)),
                ('access_token', models.CharField(max_length=255)),
                ('refresh_token', models.CharField(max_length=255, null=True)),
                ('provider_uid', models.CharField(max_length=255)),
                ('expires_at', models.PositiveIntegerField()),
                ('data', models.TextField(null=True)),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='identity',
            unique_together=set([('user', 'provider')]),
        ),
    ]
