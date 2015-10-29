# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations

from ..utils import if_es
from ..stores.es.types.profile.actions import create_mapping_v1


class Migration(migrations.Migration):

    dependencies = [
        ('search', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(if_es(create_mapping_v1)),
    ]