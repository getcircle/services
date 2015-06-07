# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0018_auto_20150607_2259'),
    ]

    operations = [
        migrations.AlterIndexTogether(
            name='device',
            index_together=set([('user', 'last_token')]),
        ),
    ]
