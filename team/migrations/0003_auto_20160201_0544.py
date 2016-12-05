# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from common.db.migrations.operations import AddRule


class Migration(migrations.Migration):

    dependencies = [
        ('team', '0002_auto_20160201_0538'),
    ]

    operations = [
        AddRule(
            'team_teammember_on_duplicate_ignore',
            'team_teammember',
            'INSERT',
            'WHERE EXISTS (SELECT 1 FROM team_teammember WHERE (profile_id, team_id, organization_id) = (NEW.profile_id, NEW.team_id, NEW.organization_id)) DO INSTEAD NOTHING',
        ),
    ]
