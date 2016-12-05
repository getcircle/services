# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0031_sso'),
    ]

    operations = [
        migrations.AddField(
            model_name='sso',
            name='provider',
            field=models.SmallIntegerField(default=0, choices=[(0, b'OKTA')]),
            preserve_default=False,
        ),
    ]
