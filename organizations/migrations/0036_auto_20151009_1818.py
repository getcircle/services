# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0035_auto_20151009_1818'),
    ]

    operations = [
        migrations.AlterField(
            model_name='teamstatus',
            name='changed',
            field=models.DateTimeField(auto_now=True),
        ),
    ]
