# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0016_auto_20150527_1754'),
    ]

    operations = [
        migrations.RunSQL('ALTER TABLE organizations_token DROP CONSTRAINT organizations_token_pkey;'),
        migrations.AddField(
            model_name='token',
            name='id',
            field=models.UUIDField(default=uuid.uuid4, serialize=False, primary_key=True),
        ),
        migrations.AlterField(
            model_name='token',
            name='key',
            field=models.CharField(max_length=40),
        ),
    ]
