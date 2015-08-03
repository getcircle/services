# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0018_auto_20150610_0157'),
    ]

    operations = [
        migrations.AddField(
            model_name='location',
            name='description',
            field=models.TextField(null=True),
        ),
        migrations.AddField(
            model_name='team',
            name='description',
            field=models.TextField(null=True),
        ),
    ]
