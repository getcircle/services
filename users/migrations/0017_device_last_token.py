# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0016_device_provider'),
    ]

    operations = [
        migrations.AddField(
            model_name='device',
            name='last_token',
            field=models.UUIDField(null=True),
        ),
    ]
