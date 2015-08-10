# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.contrib.postgres.fields.hstore


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0024_remove_team_description'),
    ]

    operations = [
        migrations.AddField(
            model_name='team',
            name='description',
            field=django.contrib.postgres.fields.hstore.HStoreField(null=True),
        ),
    ]
