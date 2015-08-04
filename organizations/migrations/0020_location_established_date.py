# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0019_auto_20150803_2148'),
    ]

    operations = [
        migrations.AddField(
            model_name='location',
            name='established_date',
            field=models.DateField(null=True),
        ),
    ]
