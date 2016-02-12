# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('team', '0004_auto_20160208_1849'),
    ]

    operations = [
        migrations.AlterField(
            model_name='contactmethod',
            name='label',
            field=models.CharField(max_length=64, null=True),
        ),
    ]
