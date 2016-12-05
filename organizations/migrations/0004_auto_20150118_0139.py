# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0003_auto_20150110_0004'),
    ]

    operations = [
        migrations.AlterField(
            model_name='address',
            name='country_code',
            field=models.CharField(max_length=64),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='address',
            name='postal_code',
            field=models.CharField(max_length=64),
            preserve_default=True,
        ),
    ]
