# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0043_auto_20160201_0456'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='reportingstructure',
            name='organization',
        ),
        migrations.AddField(
            model_name='reportingstructure',
            name='organization_id',
            field=models.UUIDField(default=uuid.uuid4, editable=False, db_index=True),
        ),
    ]
