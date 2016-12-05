# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('team', '0001_initial'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='teammember',
            unique_together=set([('team', 'profile_id')]),
        ),
    ]
