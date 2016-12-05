# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0024_auto_20151029_0647'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tag',
            name='type',
            field=models.SmallIntegerField(default=0, choices=[(0, b'SKILL'), (1, b'INTEREST'), (2, b'LANGUAGE'), (3, b'PROJECT')]),
        ),
    ]
