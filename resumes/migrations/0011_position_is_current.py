# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('resumes', '0010_auto_20150215_0421'),
    ]

    operations = [
        migrations.AddField(
            model_name='position',
            name='is_current',
            field=models.NullBooleanField(default=False),
        ),
    ]
