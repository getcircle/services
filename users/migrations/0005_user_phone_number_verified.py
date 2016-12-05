# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0004_auto_20150112_1727'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='phone_number_verified',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
    ]
