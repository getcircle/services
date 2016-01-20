# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0028_auto_20160115_0501'),
    ]

    operations = [
        migrations.AlterField(
            model_name='device',
            name='organization_id',
            field=models.UUIDField(),
        ),
        migrations.AlterField(
            model_name='identity',
            name='organization_id',
            field=models.UUIDField(),
        ),
        migrations.AlterField(
            model_name='token',
            name='organization_id',
            field=models.UUIDField(),
        ),
        migrations.AlterField(
            model_name='totptoken',
            name='organization_id',
            field=models.UUIDField(),
        ),
        migrations.AlterField(
            model_name='user',
            name='organization_id',
            field=models.UUIDField(),
        ),
    ]
