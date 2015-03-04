# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0006_auto_20150225_0122'),
    ]

    operations = [
        migrations.CreateModel(
            name='Location',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, max_length=32, serialize=False, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('changed', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=64)),
                ('address', models.ForeignKey(to='organizations.Address')),
                ('organization', models.ForeignKey(to='organizations.Organization')),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='location',
            unique_together=set([('name', 'organization')]),
        ),
    ]
