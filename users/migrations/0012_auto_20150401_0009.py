# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0011_auto_20150331_2016'),
    ]

    operations = [
        migrations.AlterField(
            model_name='device',
            name='notification_token',
            field=models.CharField(max_length=255, null=True),
        ),
    ]
