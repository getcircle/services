# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0004_auto_20150331_2238'),
    ]

    operations = [
        migrations.CreateModel(
            name='ContactMethod',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, serialize=False, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('changed', models.DateTimeField(auto_now=True)),
                ('label', models.CharField(max_length=64)),
                ('value', models.CharField(max_length=64)),
                ('type', models.SmallIntegerField(choices=[(0, b'CELL_PHONE'), (1, b'PHONE'), (2, b'EMAIL'), (3, b'SLACK'), (4, b'TWITTER'), (5, b'HIPCHAT'), (6, b'FACEBOOK'), (7, b'SKYPE')])),
                ('profile', models.ForeignKey(to='profiles.Profile')),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='contactmethod',
            unique_together=set([('profile', 'label', 'value', 'type')]),
        ),
    ]
