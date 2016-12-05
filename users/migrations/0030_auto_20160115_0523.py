# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0029_auto_20160115_0501'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='organization_id',
            field=models.UUIDField(db_index=True),
        ),
        migrations.AlterUniqueTogether(
            name='identity',
            unique_together=set([('user', 'provider', 'provider_uid', 'organization_id')]),
        ),
        migrations.AlterIndexTogether(
            name='device',
            index_together=set([('user', 'last_token_id', 'organization_id')]),
        ),
        migrations.AlterIndexTogether(
            name='token',
            index_together=set([('user', 'organization_id')]),
        ),
        migrations.AlterIndexTogether(
            name='totptoken',
            index_together=set([('user', 'organization_id')]),
        ),
    ]
