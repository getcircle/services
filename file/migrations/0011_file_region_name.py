# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('file', '0010_remove_file_source_url'),
    ]

    operations = [
        migrations.AddField(
            model_name='file',
            name='region_name',
            field=models.CharField(default=b'us-west-2', max_length=255),
        ),
    ]
