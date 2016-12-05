# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0030_auto_20150813_0630'),
    ]

    operations = [
        migrations.CreateModel(
            name='SSO',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, serialize=False, primary_key=True)),
                ('metadata_url', models.CharField(max_length=255, null=True)),
                ('metadata', models.TextField(null=True)),
                ('organization', models.ForeignKey(related_name='sso', to='organizations.Organization')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
