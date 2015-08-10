# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('history', '0003_auto_20150803_2155'),
    ]

    operations = [
        migrations.AddField(
            model_name='action',
            name='table_name',
            field=models.CharField(default='', max_length=64),
            preserve_default=False,
        ),
    ]
