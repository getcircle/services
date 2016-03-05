# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('file', '0009_auto_20160223_1117'),
    ]

    operations = [
        migrations.AddField(
            model_name='file',
            name='region_name',
            field=models.CharField(default=settings.AWS_REGION_NAME.encode('UTF-8'), max_length=255),
        ),
    ]
