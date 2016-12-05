# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0025_auto_20151029_0847'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='profiletags',
            unique_together=set([]),
        ),
        migrations.RemoveField(
            model_name='profiletags',
            name='profile',
        ),
        migrations.RemoveField(
            model_name='profiletags',
            name='tag',
        ),
        migrations.DeleteModel(
            name='Tag',
        ),
        migrations.RemoveField(
            model_name='profile',
            name='tags',
        ),
        migrations.DeleteModel(
            name='ProfileTags',
        ),
    ]
