# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import uuid


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Recent',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, serialize=False, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('changed', models.DateTimeField(auto_now=True)),
                ('by_profile_id', models.UUIDField()),
                ('organization_id', models.UUIDField()),
                ('document_type', models.CharField(max_length=255)),
                ('document_id', models.UUIDField()),
            ],
        ),
        migrations.AlterIndexTogether(
            name='recent',
            index_together=set([('organization_id', 'by_profile_id')]),
        ),
    ]
