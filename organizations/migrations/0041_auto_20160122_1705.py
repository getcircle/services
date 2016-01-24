# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0040_auto_20160122_1614'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='sso',
            name='metadata',
        ),
        migrations.RemoveField(
            model_name='sso',
            name='metadata_url',
        ),
        migrations.AlterField(
            model_name='sso',
            name='organization',
            field=models.OneToOneField(related_name='sso', to='organizations.Organization'),
        ),
    ]
