# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0030_auto_20160201_0456'),
    ]

    operations = [
        migrations.AlterField(
            model_name='contactmethod',
            name='type',
            field=models.SmallIntegerField(default=0, choices=[(0, b'CELL_PHONE'), (1, b'EMAIL'), (2, b'SLACK')]),
        ),
    ]
