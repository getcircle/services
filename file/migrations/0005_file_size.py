# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('file', '0004_auto_20151209_0834'),
    ]

    operations = [
        migrations.AddField(
            model_name='file',
            name='size',
            field=models.BigIntegerField(null=True),
        ),
    ]
