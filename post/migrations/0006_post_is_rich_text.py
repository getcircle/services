# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('post', '0005_auto_20151116_0238'),
    ]

    operations = [
        migrations.AddField(
            model_name='post',
            name='is_rich_text',
            field=models.BooleanField(default=False),
        ),
    ]
