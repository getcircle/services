# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0027_location_description'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='address',
            unique_together=set([]),
        ),
        migrations.RemoveField(
            model_name='address',
            name='organization',
        ),
        migrations.AlterUniqueTogether(
            name='location',
            unique_together=set([]),
        ),
        migrations.RemoveField(
            model_name='location',
            name='address',
        ),
        migrations.RemoveField(
            model_name='location',
            name='organization',
        ),
        migrations.AlterUniqueTogether(
            name='team',
            unique_together=set([]),
        ),
        migrations.RemoveField(
            model_name='team',
            name='organization',
        ),
        migrations.AlterIndexTogether(
            name='teamstatus',
            index_together=set([]),
        ),
        migrations.RemoveField(
            model_name='teamstatus',
            name='team',
        ),
        migrations.DeleteModel(
            name='Address',
        ),
        migrations.DeleteModel(
            name='Location',
        ),
        migrations.DeleteModel(
            name='Team',
        ),
        migrations.DeleteModel(
            name='TeamStatus',
        ),
    ]
