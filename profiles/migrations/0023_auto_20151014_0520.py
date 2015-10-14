# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0022_auto_20151013_0510'),
    ]

    operations = [
        migrations.AlterIndexTogether(
            name='profilestatus',
            index_together=set([('profile', 'organization_id', 'created'), ('value', 'organization_id')]),
        ),
    ]
