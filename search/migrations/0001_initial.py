# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations

from ..stores.es.indices.search_v1.actions import create_index


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.RunPython(create_index),
    ]
