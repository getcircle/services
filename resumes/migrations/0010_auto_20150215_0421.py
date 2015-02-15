# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations
from common.db.migrations.operations import AddRule


class Migration(migrations.Migration):

    dependencies = [
        ('resumes', '0009_auto_20150215_0414'),
    ]

    operations = [
        AddRule(
            'resumes_position_on_duplicate_ignore',
            'resumes_position',
            'INSERT',
            'WHERE EXISTS (SELECT 1 FROM resumes_position WHERE (user_id, title, company_id) = (NEW.user_id, NEW.title, NEW.company_id)) DO INSTEAD NOTHING',
        )
    ]
