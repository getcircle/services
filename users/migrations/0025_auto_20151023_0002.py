# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0024_auto_20150925_0525'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='identity',
            unique_together=set([('user', 'provider', 'provider_uid')]),
        ),
    ]
