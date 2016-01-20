# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0030_auto_20160115_0523'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='primary_email',
            field=models.EmailField(max_length=254),
        ),
        migrations.AlterUniqueTogether(
            name='user',
            unique_together=set([('primary_email', 'organization_id')]),
        ),
    ]
