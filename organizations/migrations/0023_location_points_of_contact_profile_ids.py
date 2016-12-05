# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.contrib.postgres.fields


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0022_team_image_url'),
    ]

    operations = [
        migrations.AddField(
            model_name='location',
            name='points_of_contact_profile_ids',
            field=django.contrib.postgres.fields.ArrayField(null=True, base_field=models.UUIDField(), size=None),
        ),
    ]
