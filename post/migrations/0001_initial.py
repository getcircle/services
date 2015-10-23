# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import uuid


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Post',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, serialize=False, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('changed', models.DateTimeField(auto_now=True)),
                ('title', models.CharField(max_length=255)),
                ('content', models.TextField()),
                ('organization_id', models.UUIDField()),
                ('by_profile_id', models.UUIDField()),
                ('state', models.SmallIntegerField(choices=[(0, b'DRAFT'), (1, b'LISTED'), (2, b'UNLISTED')])),
            ],
        ),
        migrations.AlterIndexTogether(
            name='post',
            index_together=set([('organization_id', 'by_profile_id')]),
        ),
    ]
