# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('history', '0007_auto_20160201_0456'),
    ]

    operations = [
        migrations.AlterField(
            model_name='action',
            name='action_type',
            field=models.SmallIntegerField(default=0, choices=[(0, b'UPDATE_DESCRIPTION'), (1, b'CREATE_INSTANCE')]),
            preserve_default=False,
        ),
    ]
