# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0028_syncsettings'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='status',
            field=models.SmallIntegerField(default=0, choices=[(0, b'ACTIVE'), (1, b'INACTIVE')]),
        ),
    ]
