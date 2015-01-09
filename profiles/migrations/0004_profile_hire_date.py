# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0003_profile_birth_date'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='hire_date',
            field=models.DateField(default=datetime.datetime(2015, 1, 9, 19, 43, 26, 603086, tzinfo=utc)),
            preserve_default=False,
        ),
    ]
