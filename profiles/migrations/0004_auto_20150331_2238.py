# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0003_profile_nickname'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='profile',
            name='cell_phone',
        ),
        migrations.RemoveField(
            model_name='profile',
            name='email',
        ),
        migrations.RemoveField(
            model_name='profile',
            name='work_phone',
        ),
    ]
