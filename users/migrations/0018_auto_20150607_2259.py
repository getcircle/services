# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0017_device_last_token'),
    ]

    operations = [
        migrations.AlterField(
            model_name='device',
            name='last_token',
            field=models.CharField(max_length=40, null=True),
        ),
    ]
