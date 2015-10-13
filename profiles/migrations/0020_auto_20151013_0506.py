# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0019_auto_20151009_1845'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='authentication_identifier',
            field=models.CharField(max_length=255, null=True),
        ),
        migrations.AlterUniqueTogether(
            name='profile',
            unique_together=set([('organization_id', 'authentication_identifier'), ('organization_id', 'user_id')]),
        ),
    ]
