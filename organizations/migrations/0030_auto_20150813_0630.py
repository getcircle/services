# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0029_auto_20150812_2114'),
    ]

    operations = [
        migrations.AlterField(
            model_name='team',
            name='created_by_profile_id',
            field=models.UUIDField(null=True, editable=False),
        ),
    ]
