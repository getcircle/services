# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('file', '0003_file_content_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='file',
            name='content_type',
            field=models.CharField(max_length=255),
        ),
    ]
