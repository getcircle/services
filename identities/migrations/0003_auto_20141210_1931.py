# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('identities', '0002_auto_20141210_1920'),
    ]

    operations = [
        migrations.AlterField(
            model_name='identity',
            name='type',
            field=models.PositiveSmallIntegerField(default=0, choices=[(0, b'INTERNAL')]),
            preserve_default=True,
        ),
    ]
