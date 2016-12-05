# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('post', '0005_auto_20151116_0238'),
    ]

    operations = [
        migrations.AddField(
            model_name='post',
            name='source',
            field=models.SmallIntegerField(default=0, choices=[(0, b'LUNO'), (1, b'EMAIL'), (2, b'SLACK')]),
        ),
        migrations.AddField(
            model_name='post',
            name='source_id',
            field=models.CharField(max_length=255, null=True),
        ),
    ]
