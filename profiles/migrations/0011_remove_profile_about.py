# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0010_contactmethod_organization_id'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='profile',
            name='about',
        ),
    ]
