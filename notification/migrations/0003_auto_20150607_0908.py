# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('notification', '0002_auto_20150606_2109'),
    ]

    operations = [
        migrations.AddField(
            model_name='notificationtoken',
            name='provider_platform',
            field=models.SmallIntegerField(null=True, choices=[(0, b'APNS'), (1, b'GCM')]),
        ),
        migrations.AlterField(
            model_name='notificationtoken',
            name='provider',
            field=models.SmallIntegerField(choices=[(0, b'SNS')]),
        ),
        migrations.AlterUniqueTogether(
            name='notificationpreference',
            unique_together=set([('profile_id', 'notification_type')]),
        ),
    ]
