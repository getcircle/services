# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0002_auto_20141231_2048'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='birth_date',
            field=models.DateField(default=datetime.datetime(2015, 1, 9, 19, 37, 57, 828187, tzinfo=utc)),
            preserve_default=False,
        ),
    ]
