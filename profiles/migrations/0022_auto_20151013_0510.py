# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0021_auto_20151013_0507'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profile',
            name='authentication_identifier',
            field=models.CharField(max_length=255),
        ),
    ]
