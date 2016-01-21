# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('glossary', '0002_auto_20150602_0024'),
    ]

    operations = [
        migrations.DeleteModel(
            name='Term',
        ),
    ]
