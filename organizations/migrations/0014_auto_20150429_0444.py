# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0013_token'),
    ]

    operations = [
        migrations.RenameField(
            model_name='token',
            old_name='organization_id',
            new_name='organization',
        ),
    ]
