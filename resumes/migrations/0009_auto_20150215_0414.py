# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('resumes', '0008_auto_20150215_0305'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='position',
            unique_together=set([('user_id', 'title', 'company')]),
        ),
    ]
