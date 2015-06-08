# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0020_auto_20150608_0355'),
    ]

    operations = [
        migrations.AddField(
            model_name='device',
            name='last_token_id',
            field=models.UUIDField(null=True),
        ),
        migrations.AlterIndexTogether(
            name='device',
            index_together=set([('user', 'last_token_id')]),
        ),
        migrations.RemoveField(
            model_name='device',
            name='last_token',
        ),
    ]
