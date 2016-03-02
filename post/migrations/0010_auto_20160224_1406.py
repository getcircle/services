# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('post', '0009_auto_20160212_2047'),
    ]

    operations = [
        migrations.AlterField(
            model_name='collection',
            name='name',
            field=models.CharField(max_length=64, null=True),
        ),
    ]
