# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('notification', '0003_auto_20150607_0908'),
    ]

    operations = [
        migrations.AlterField(
            model_name='notificationpreference',
            name='notification_type',
            field=models.ForeignKey(related_name='preferences', to='notification.NotificationType'),
        ),
    ]
