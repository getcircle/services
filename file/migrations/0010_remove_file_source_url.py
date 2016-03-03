# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('file', '0009_auto_20160223_1117'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='file',
            name='source_url',
        ),
    ]
