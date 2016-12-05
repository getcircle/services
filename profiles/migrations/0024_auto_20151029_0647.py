# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0023_auto_20151014_0520'),
    ]

    operations = [
        migrations.AlterField(
            model_name='contactmethod',
            name='type',
            field=models.SmallIntegerField(default=0, choices=[(0, b'CELL_PHONE'), (1, b'PHONE'), (2, b'EMAIL'), (3, b'SLACK'), (4, b'TWITTER'), (5, b'HIPCHAT'), (6, b'FACEBOOK'), (7, b'SKYPE')]),
        ),
    ]
