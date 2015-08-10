# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.contrib.postgres.fields.hstore


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0026_remove_location_description'),
    ]

    operations = [
        migrations.AddField(
            model_name='location',
            name='description',
            field=django.contrib.postgres.fields.hstore.HStoreField(null=True),
        ),
    ]
