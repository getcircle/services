# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('resumes', '0003_auto_20150215_0009'),
    ]

    operations = [
        migrations.AddField(
            model_name='education',
            name='activities',
            field=models.TextField(null=True),
        ),
    ]
