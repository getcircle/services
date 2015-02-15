# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('resumes', '0006_auto_20150215_0124'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='education',
            unique_together=set([('user_id', 'school_name', 'start_date', 'end_date')]),
        ),
    ]
