# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0012_auto_20150401_0009'),
    ]

    operations = [
        migrations.AddField(
            model_name='device',
            name='language_preference',
            field=models.CharField(default='en', max_length=16),
            preserve_default=False,
        ),
    ]
