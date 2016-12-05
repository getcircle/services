# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('notification', '0005_auto_20160115_1806'),
    ]

    operations = [
        migrations.AlterField(
            model_name='notificationtoken',
            name='organization_id',
            field=models.UUIDField(),
        ),
    ]
