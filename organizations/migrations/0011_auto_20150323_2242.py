# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0010_location_image_url'),
    ]

    operations = [
        migrations.RunSQL(
            'CREATE INDEX organizations_team_path_gist_idx ON organizations_team USING GIST (path);',
            'DROP INDEX organizations_team_path_gist_idx',
        ),
    ]
