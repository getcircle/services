# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations

from ..stores.es.types.team.actions import create_mapping_v1


class Migration(migrations.Migration):

    dependencies = [
        ('search', '0002_auto_20151028_1832'),
    ]

    operations = [
        migrations.RunPython(create_mapping_v1),
    ]
