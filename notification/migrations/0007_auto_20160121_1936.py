# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('notification', '0006_auto_20160115_1806'),
    ]

    operations = [
        migrations.AlterField(
            model_name='notificationpreference',
            name='subscribed',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterIndexTogether(
            name='notificationtoken',
            index_together=set([('user_id', 'provider', 'organization_id')]),
        ),
    ]
