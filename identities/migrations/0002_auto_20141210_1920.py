# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('identities', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='identity',
            name='type',
            field=models.PositiveSmallIntegerField(default=0, choices=[(0, b'Internal')]),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='identity',
            unique_together=set([('type', 'email')]),
        ),
    ]
