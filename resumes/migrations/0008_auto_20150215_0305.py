# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations
from common.db.migrations.operations import AddRule


class Migration(migrations.Migration):

    dependencies = [
        ('resumes', '0007_auto_20150215_0304'),
    ]

    operations = [
        AddRule(
            'resumes_education_on_duplicate_ignore',
            'resumes_education',
            'INSERT',
            'WHERE EXISTS (SELECT 1 FROM resumes_education WHERE (user_id, school_name, start_date, end_date) = (NEW.user_id, NEW.school_name, NEW.start_date, NEW.end_date)) DO INSTEAD NOTHING',
        )
    ]
