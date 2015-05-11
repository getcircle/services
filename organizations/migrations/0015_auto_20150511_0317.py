# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0014_auto_20150429_0444'),
    ]

    operations = [
        migrations.AlterField(
            model_name='token',
            name='requested_by_user_id',
            field=models.UUIDField(null=True),
        ),
    ]
