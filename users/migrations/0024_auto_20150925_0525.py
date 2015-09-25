# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0023_auto_20150922_2005'),
    ]

    operations = [
        migrations.AlterField(
            model_name='identity',
            name='provider',
            field=models.PositiveSmallIntegerField(choices=[(0, b'INTERNAL'), (1, b'LINKEDIN'), (2, b'GOOGLE'), (3, b'OKTA')]),
        ),
    ]
