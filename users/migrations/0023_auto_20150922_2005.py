# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0022_auto_20150921_1854'),
    ]

    operations = [
        migrations.AlterField(
            model_name='identity',
            name='access_token',
            field=models.CharField(max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='identity',
            name='expires_at',
            field=models.PositiveIntegerField(null=True),
        ),
        migrations.AlterField(
            model_name='identity',
            name='full_name',
            field=models.CharField(max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='identity',
            name='provider',
            field=models.PositiveSmallIntegerField(choices=[(0, b'INTERNAL'), (1, b'LINKEDIN'), (2, b'GOOGLE'), (3, b'SAML')]),
        ),
    ]
