# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('appreciation', '0002_auto_20150228_1938'),
    ]

    operations = [
        migrations.AddField(
            model_name='appreciation',
            name='status',
            field=models.PositiveSmallIntegerField(null=True, choices=[(1, b'Deleted')]),
        ),
    ]
