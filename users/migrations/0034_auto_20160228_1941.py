# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0033_auto_20160201_0456'),
    ]

    operations = [
        migrations.AlterField(
            model_name='identity',
            name='provider',
            field=models.PositiveSmallIntegerField(choices=[(0, b'INTERNAL'), (1, b'LINKEDIN'), (2, b'GOOGLE'), (3, b'OKTA'), (4, b'SLACK')]),
        ),
    ]
