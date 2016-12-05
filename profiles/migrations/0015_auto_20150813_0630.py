# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0014_profile_tags'),
    ]

    operations = [
        migrations.AlterField(
            model_name='contactmethod',
            name='profile',
            field=models.ForeignKey(related_name='contact_methods', to='profiles.Profile'),
        ),
    ]
