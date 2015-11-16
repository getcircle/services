# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('post', '0004_auto_20151109_0052'),
    ]

    operations = [
        migrations.AlterIndexTogether(
            name='post',
            index_together=set([('organization_id', 'by_profile_id'), ('organization_id', 'state')]),
        ),
    ]
