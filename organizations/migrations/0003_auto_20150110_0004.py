# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0002_auto_20150109_1753'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='address',
            unique_together=set([('name', 'organization')]),
        ),
    ]
