# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0015_auto_20150528_2131'),
    ]

    operations = [
        migrations.AddField(
            model_name='device',
            name='provider',
            field=models.SmallIntegerField(null=True, choices=[(0, b'APPLE'), (1, b'GOOGLE')]),
        ),
    ]
