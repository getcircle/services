# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='changed',
            field=models.DateTimeField(default=datetime.datetime(2014, 12, 10, 3, 54, 59, 393193, tzinfo=utc), auto_now=True),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='user',
            name='created',
            field=models.DateTimeField(default=datetime.datetime(2014, 12, 10, 3, 55, 4, 505447, tzinfo=utc), auto_now_add=True),
            preserve_default=False,
        ),
    ]
