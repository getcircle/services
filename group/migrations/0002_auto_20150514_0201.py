# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.contrib.postgres.fields


class Migration(migrations.Migration):

    dependencies = [
        ('group', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='groupmembershiprequest',
            name='approver_profile_id',
        ),
        migrations.AddField(
            model_name='groupmembershiprequest',
            name='approver_profile_ids',
            field=django.contrib.postgres.fields.ArrayField(null=True, base_field=models.UUIDField(), size=None),
        ),
    ]
