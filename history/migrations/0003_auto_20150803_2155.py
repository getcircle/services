# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('history', '0002_auto_20150803_2034'),
    ]

    operations = [
        migrations.AlterField(
            model_name='action',
            name='old_value',
            field=models.TextField(null=True),
        ),
    ]
