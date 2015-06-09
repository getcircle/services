# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0008_profile_is_admin'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='small_image_url',
            field=models.URLField(max_length=256, null=True),
        ),
    ]
