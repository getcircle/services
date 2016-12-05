# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0023_location_points_of_contact_profile_ids'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='team',
            name='description',
        ),
    ]
