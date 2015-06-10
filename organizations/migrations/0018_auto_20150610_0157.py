# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import organizations.models


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0017_auto_20150608_0434'),
    ]

    operations = [
        migrations.AlterField(
            model_name='team',
            name='organization',
            field=models.ForeignKey(editable=False, to='organizations.Organization'),
        ),
        migrations.AlterField(
            model_name='team',
            name='owner_id',
            field=models.UUIDField(editable=False, db_index=True),
        ),
        migrations.AlterField(
            model_name='team',
            name='path',
            field=organizations.models.LTreeField(null=True, editable=False, db_index=True),
        ),
    ]
