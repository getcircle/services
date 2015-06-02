# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('glossary', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='term',
            name='created_by_profile_id',
            field=models.UUIDField(editable=False),
        ),
        migrations.AlterField(
            model_name='term',
            name='organization_id',
            field=models.UUIDField(editable=False, db_index=True),
        ),
    ]
