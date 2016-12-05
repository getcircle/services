# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0015_auto_20150813_0630'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profilestatus',
            name='profile',
            field=models.ForeignKey(related_name='statuses', to='profiles.Profile'),
        ),
    ]
