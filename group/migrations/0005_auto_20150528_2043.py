# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.contrib.postgres.fields


class Migration(migrations.Migration):

    dependencies = [
        ('group', '0004_auto_20150527_0433'),
    ]

    operations = [
        migrations.AlterField(
            model_name='groupmembershiprequest',
            name='approver_profile_ids',
            field=django.contrib.postgres.fields.ArrayField(size=None, null=True, base_field=models.UUIDField(), db_index=True),
        ),
        migrations.AlterField(
            model_name='groupmembershiprequest',
            name='requester_profile_id',
            field=models.UUIDField(db_index=True),
        ),
        migrations.AlterIndexTogether(
            name='groupmembershiprequest',
            index_together=set([('provider', 'group_key')]),
        ),
    ]
