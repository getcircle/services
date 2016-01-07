# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('post', '0006_auto_20160107_2143'),
    ]

    operations = [
        migrations.AlterField(
            model_name='post',
            name='source',
            field=models.SmallIntegerField(default=0, choices=[(0, b'WEB'), (1, b'EMAIL'), (2, b'SLACK')]),
        ),
    ]
