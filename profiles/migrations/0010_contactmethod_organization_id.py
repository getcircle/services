# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0009_profile_small_image_url'),
    ]

    operations = [
        migrations.AddField(
            model_name='contactmethod',
            name='organization_id',
            field=models.UUIDField(default='0e55d3de-d3e6-4540-ad0a-015966907bfe'),
            preserve_default=False,
        ),
    ]
