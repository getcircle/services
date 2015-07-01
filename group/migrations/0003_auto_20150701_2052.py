# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('group', '0002_auto_20150612_0045'),
    ]

    operations = [
        migrations.AlterField(
            model_name='googlegroup',
            name='direct_members_count',
            field=models.PositiveIntegerField(default=0),
        ),
    ]
