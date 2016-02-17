# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0044_auto_20160217_2146'),
    ]

    operations = [
        migrations.AlterField(
            model_name='reportingstructure',
            name='organization_id',
            field=models.UUIDField(editable=False, db_index=True),
        ),
    ]
