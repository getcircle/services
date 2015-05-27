# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('group', '0003_auto_20150514_0256'),
    ]

    operations = [
        migrations.AlterField(
            model_name='groupmembershiprequest',
            name='status',
            field=models.SmallIntegerField(choices=[(0, b'PENDING'), (1, b'APPROVED'), (2, b'DENIED')]),
        ),
    ]
