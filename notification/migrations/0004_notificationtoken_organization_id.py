# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('notification', '0003_auto_20150805_0433'),
    ]

    operations = [
        migrations.AddField(
            model_name='notificationtoken',
            name='organization_id',
            field=models.UUIDField(null=True),
        ),
    ]
