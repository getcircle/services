# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='address',
            old_name='organization_id',
            new_name='organization',
        ),
    ]
