# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations
from common.db.migrations.operations import AddRule


class Migration(migrations.Migration):

    dependencies = [
        ('resumes', '0005_auto_20150215_0051'),
    ]

    operations = [
        AddRule(
            'resumes_company_on_duplicate_ignore',
            'resumes_company',
            'INSERT',
            'WHERE EXISTS (SELECT 1 FROM resumes_company WHERE name = NEW.name) DO INSTEAD NOTHING',
        )
    ]
