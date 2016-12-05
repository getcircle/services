# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('file', '0008_auto_20160223_1110'),
    ]

    operations = [
        migrations.AlterField(
            model_name='file',
            name='key',
            field=models.CharField(max_length=255),
        ),
    ]
