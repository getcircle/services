# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django_date_extensions.fields


class Migration(migrations.Migration):

    dependencies = [
        ('resumes', '0002_auto_20150214_2201'),
    ]

    operations = [
        migrations.AlterField(
            model_name='education',
            name='end_date',
            field=django_date_extensions.fields.ApproximateDateField(max_length=10, null=True),
        ),
        migrations.AlterField(
            model_name='education',
            name='start_date',
            field=django_date_extensions.fields.ApproximateDateField(max_length=10, null=True),
        ),
        migrations.AlterField(
            model_name='education',
            name='user_id',
            field=models.UUIDField(max_length=32, db_index=True),
        ),
        migrations.AlterField(
            model_name='position',
            name='end_date',
            field=django_date_extensions.fields.ApproximateDateField(max_length=10, null=True),
        ),
        migrations.AlterField(
            model_name='position',
            name='start_date',
            field=django_date_extensions.fields.ApproximateDateField(max_length=10, null=True),
        ),
        migrations.AlterField(
            model_name='position',
            name='user_id',
            field=models.UUIDField(max_length=32, db_index=True),
        ),
    ]
