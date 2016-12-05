# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations
from common.db.migrations.operations import AddRule


class Migration(migrations.Migration):

    dependencies = [
       ('profiles', '0001_initial'),
    ]

    operations = [
        AddRule(
            'profiles_tag_on_duplicate_ignore',
            'profiles_tag',
            'INSERT',
            'WHERE EXISTS (SELECT 1 FROM profiles_tag WHERE (name, organization_id, type) = (NEW.name, NEW.organization_id, NEW.type)) DO INSTEAD NOTHING',
        )
    ]
