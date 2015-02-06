# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations
from common.db.migrations.operations import AddRule


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0003_auto_20150206_2102'),
    ]

    operations = [
        AddRule(
            'profiles_skill_on_duplicate_ignore',
            'profiles_skill',
            'INSERT',
            'WHERE EXISTS (SELECT 1 FROM profiles_skill WHERE (name, organization_id) = (NEW.name, NEW.organization_id)) DO INSTEAD NOTHING',
        )
    ]
