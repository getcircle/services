# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0037_auto_20151110_0031'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='token',
            name='organization',
        ),
        migrations.DeleteModel(
            name='Token',
        ),
    ]
