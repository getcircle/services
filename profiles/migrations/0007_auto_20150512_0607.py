# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0006_profile_email'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profile',
            name='birth_date',
            field=models.DateField(null=True),
        ),
        migrations.AlterField(
            model_name='profile',
            name='hire_date',
            field=models.DateField(null=True),
        ),
    ]
