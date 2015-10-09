# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0016_auto_20150813_0755'),
    ]

    operations = [
        migrations.AddField(
            model_name='profilestatus',
            name='changed',
            field=models.DateTimeField(auto_now=True, null=True),
        ),
    ]
