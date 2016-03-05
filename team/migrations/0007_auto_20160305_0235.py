# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('team', '0006_auto_20160229_0833'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='team',
            unique_together=set([]),
        ),
    ]
