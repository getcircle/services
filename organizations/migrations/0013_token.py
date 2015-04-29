# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0012_auto_20150323_2249'),
    ]

    operations = [
        migrations.CreateModel(
            name='Token',
            fields=[
                ('key', models.CharField(max_length=40, serialize=False, primary_key=True)),
                ('requested_by_user_id', models.UUIDField()),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('organization_id', models.ForeignKey(related_name='auth_token', to='organizations.Organization')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
