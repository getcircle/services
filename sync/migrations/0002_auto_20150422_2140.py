# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sync', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='syncjournal',
            name='journal_type',
            field=models.SmallIntegerField(choices=[(b'SyncCompleted', 0), (b'RecordProcessed', 1)]),
        ),
    ]
