# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0025_auto_20151023_0002'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='accessrequest',
            name='user',
        ),
        migrations.DeleteModel(
            name='AccessRequest',
        ),
    ]
