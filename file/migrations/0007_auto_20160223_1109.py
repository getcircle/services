# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('file', '0006_auto_20160201_0456'),
    ]

    operations = [
        migrations.AddField(
            model_name='file',
            name='bucket',
            field=models.CharField(default=b'dev-lunohq-files', max_length=64),
        ),
        migrations.AddField(
            model_name='file',
            name='key',
            field=models.CharField(max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='file',
            name='organization_id',
            field=models.UUIDField(),
        ),
        migrations.AlterIndexTogether(
            name='file',
            index_together=set([('id', 'organization_id')]),
        ),
    ]
