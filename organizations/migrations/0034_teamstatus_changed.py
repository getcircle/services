# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0033_auto_20151006_0722'),
    ]

    operations = [
        migrations.AddField(
            model_name='teamstatus',
            name='changed',
            field=models.DateTimeField(auto_now=True, null=True),
        ),
    ]
