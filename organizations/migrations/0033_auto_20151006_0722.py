# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from common.db.migrations.operations import AddRule


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0032_sso_provider'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='locationmember',
            unique_together=set([('profile_id', 'location')]),
        ),
        AddRule(
            'organizations_locationmember_on_duplicate_ignore',
            'organizations_locationmember',
            'INSERT',
            'WHERE EXISTS (SELECT 1 FROM organizations_locationmember WHERE (profile_id, location_id) = (NEW.profile_id, NEW.location_id)) DO INSTEAD NOTHING',
        ),
    ]
