# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('file', '0002_file_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='file',
            name='content_type',
            field=models.CharField(default='text/plain', max_length=64),
            preserve_default=False,
        ),
    ]
