# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.contrib.postgres.fields.hstore


class Migration(migrations.Migration):

    dependencies = [
        ('group', '0002_auto_20150514_0201'),
    ]

    operations = [
        migrations.AlterField(
            model_name='groupmembershiprequest',
            name='meta',
            field=django.contrib.postgres.fields.hstore.HStoreField(null=True),
        ),
    ]
