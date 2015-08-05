# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('notification', '0002_auto_20150802_0135'),
    ]

    operations = [
        migrations.AlterField(
            model_name='notificationtoken',
            name='device_id',
            field=models.UUIDField(db_index=True),
        ),
    ]
