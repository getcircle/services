# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import organizations.models


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0011_auto_20150323_2242'),
    ]

    operations = [
        migrations.AlterField(
            model_name='team',
            name='path',
            field=organizations.models.LTreeField(null=True, db_index=True),
        ),
    ]
