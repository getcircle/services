# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0008_address_timezone'),
    ]

    operations = [
        migrations.AddField(
            model_name='organization',
            name='image_url',
            field=models.URLField(max_length=255, null=True),
        ),
    ]
