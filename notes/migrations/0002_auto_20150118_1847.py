# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('notes', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='note',
            name='for_user',
        ),
        migrations.RemoveField(
            model_name='note',
            name='user',
        ),
        migrations.AddField(
            model_name='note',
            name='for_profile_id',
            field=models.UUIDField(default='6ca86013-e6c7-41a3-8688-0696c4bdc91e', max_length=32),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='note',
            name='owner_profile_id',
            field=models.UUIDField(default='6ca86013-e6c7-41a3-8688-0696c4bdc91e', max_length=32),
            preserve_default=False,
        ),
    ]
