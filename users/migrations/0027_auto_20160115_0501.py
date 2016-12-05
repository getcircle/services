# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0026_auto_20160115_0257'),
    ]

    operations = [
        migrations.AddField(
            model_name='device',
            name='organization_id',
            field=models.UUIDField(null=True),
        ),
        migrations.AddField(
            model_name='identity',
            name='organization_id',
            field=models.UUIDField(null=True),
        ),
        migrations.AddField(
            model_name='token',
            name='organization_id',
            field=models.UUIDField(null=True),
        ),
        migrations.AddField(
            model_name='totptoken',
            name='organization_id',
            field=models.UUIDField(null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='organization_id',
            field=models.UUIDField(null=True),
        ),
    ]
