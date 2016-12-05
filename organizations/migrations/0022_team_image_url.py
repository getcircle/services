# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0021_auto_20150804_0316'),
    ]

    operations = [
        migrations.AddField(
            model_name='team',
            name='image_url',
            field=models.URLField(max_length=255, null=True),
        ),
    ]
