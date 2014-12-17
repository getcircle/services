# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings
import phonenumber_field.modelfields
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Identity',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, max_length=32, serialize=False, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('changed', models.DateTimeField(auto_now=True)),
                ('first_name', models.CharField(max_length=64, null=True)),
                ('last_name', models.CharField(max_length=64, null=True)),
                ('type', models.PositiveSmallIntegerField(default=0, choices=[(0, b'INTERNAL')])),
                ('email', models.EmailField(max_length=254)),
                ('phone_number', phonenumber_field.modelfields.PhoneNumberField(max_length=128, null=True)),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='identity',
            unique_together=set([('type', 'email')]),
        ),
    ]
