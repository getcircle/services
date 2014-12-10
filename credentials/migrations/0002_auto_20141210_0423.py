# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('credentials', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='credential',
            name='changed',
            field=models.DateTimeField(default=datetime.datetime(2014, 12, 10, 4, 23, 54, 743916, tzinfo=utc), auto_now=True),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='credential',
            name='created',
            field=models.DateTimeField(default=datetime.datetime(2014, 12, 10, 4, 23, 59, 224089, tzinfo=utc), auto_now_add=True),
            preserve_default=False,
        ),
    ]
