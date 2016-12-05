# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('history', '0008_auto_20160201_0512'),
    ]

    operations = [
        migrations.AlterField(
            model_name='action',
            name='action_type',
            field=models.SmallIntegerField(choices=[(0, b'UPDATE_DESCRIPTION'), (1, b'CREATE_INSTANCE'), (2, b'UPDATE_TEAM_MEMBER_ROLE')]),
        ),
    ]
