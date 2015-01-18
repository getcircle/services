# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0004_auto_20150118_0139'),
    ]

    operations = [
        migrations.AddField(
            model_name='address',
            name='latitude',
            field=models.DecimalField(default=0, max_digits=10, decimal_places=6),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='address',
            name='longitude',
            field=models.DecimalField(default=0, max_digits=10, decimal_places=6),
            preserve_default=False,
        ),
    ]
