# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('notification', '0004_auto_20150607_2152'),
    ]

    operations = [
        migrations.AlterField(
            model_name='notificationtype',
            name='id',
            field=models.SmallIntegerField(serialize=False, primary_key=True, choices=[(0, b'GOOGLE_GROUPS')]),
        ),
    ]
