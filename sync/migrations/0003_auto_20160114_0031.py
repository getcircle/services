# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sync', '0002_auto_20150422_2140'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='syncjournal',
            unique_together=set([]),
        ),
        migrations.RemoveField(
            model_name='syncjournal',
            name='record',
        ),
        migrations.RemoveField(
            model_name='syncjournal',
            name='sync',
        ),
        migrations.RemoveField(
            model_name='syncrecord',
            name='sync',
        ),
        migrations.DeleteModel(
            name='SyncJournal',
        ),
        migrations.DeleteModel(
            name='SyncRecord',
        ),
        migrations.DeleteModel(
            name='SyncRequest',
        ),
    ]
