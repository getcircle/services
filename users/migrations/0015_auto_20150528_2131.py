# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0014_token'),
    ]

    operations = [
        migrations.AlterField(
            model_name='device',
            name='language_preference',
            field=models.CharField(default=b'en', max_length=16),
        ),
    ]
