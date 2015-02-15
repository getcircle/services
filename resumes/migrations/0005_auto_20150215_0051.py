# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('resumes', '0004_education_activities'),
    ]

    operations = [
        migrations.AddField(
            model_name='education',
            name='degree',
            field=models.CharField(max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='education',
            name='field_of_study',
            field=models.CharField(max_length=255, null=True),
        ),
    ]
