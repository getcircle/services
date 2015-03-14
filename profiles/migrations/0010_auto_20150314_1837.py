# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0009_auto_20150302_2325'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profile',
            name='image_url',
            field=models.URLField(max_length=256, null=True),
        ),
    ]
