# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0025_team_description'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='location',
            name='description',
        ),
    ]
