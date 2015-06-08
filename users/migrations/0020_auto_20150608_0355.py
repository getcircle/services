# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0019_auto_20150607_2313'),
    ]

    operations = [
        migrations.RunSQL('ALTER TABLE users_token DROP CONSTRAINT users_token_pkey;'),
        migrations.AddField(
            model_name='token',
            name='id',
            field=models.UUIDField(default=uuid.uuid4, serialize=False, primary_key=True),
        ),
        migrations.AlterField(
            model_name='token',
            name='key',
            field=models.CharField(max_length=40, db_index=True),
        ),
    ]
