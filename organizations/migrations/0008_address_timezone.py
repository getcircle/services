# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import timezone_field.fields


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0007_auto_20150302_2217'),
    ]

    operations = [
        migrations.AddField(
            model_name='address',
            name='timezone',
            field=timezone_field.fields.TimeZoneField(default='America/Los_Angeles'),
            preserve_default=False,
        ),
    ]
