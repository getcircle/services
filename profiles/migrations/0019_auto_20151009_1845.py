# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0018_auto_20151009_1845'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profilestatus',
            name='changed',
            field=models.DateTimeField(auto_now=True),
        ),
    ]
