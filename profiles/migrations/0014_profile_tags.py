# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0013_auto_20150812_0033'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='tags',
            field=models.ManyToManyField(to='profiles.Tag', through='profiles.ProfileTags'),
        ),
    ]
