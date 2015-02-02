# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0006_auto_20150202_0119'),
    ]

    operations = [
        migrations.RenameField(
            model_name='identity',
            old_name='name',
            new_name='full_name',
        ),
    ]
