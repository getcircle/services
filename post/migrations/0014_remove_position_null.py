# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('post', '0013_populate_position_values'),
    ]

    operations = [
        migrations.AlterField(
            model_name='collection',
            name='position',
            field=models.PositiveSmallIntegerField(),
        ),
    ]
