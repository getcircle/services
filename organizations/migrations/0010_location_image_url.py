# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0009_organization_image_url'),
    ]

    operations = [
        migrations.AddField(
            model_name='location',
            name='image_url',
            field=models.URLField(max_length=255, null=True),
        ),
    ]
