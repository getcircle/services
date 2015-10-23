# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('post', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='post',
            name='state',
            field=models.SmallIntegerField(default=0, choices=[(0, b'DRAFT'), (1, b'LISTED'), (2, b'UNLISTED')]),
        ),
    ]
