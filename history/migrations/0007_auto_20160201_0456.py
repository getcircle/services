# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('history', '0006_auto_20160130_2155'),
    ]

    operations = [
        migrations.AlterField(
            model_name='action',
            name='method_type',
            field=models.SmallIntegerField(choices=[(0, b'UPDATE'), (1, b'DELETE'), (2, b'CREATE')]),
        ),
    ]
