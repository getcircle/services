# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


def default_authentication_identifier_to_email(apps, schema_editor):
    Profile = apps.get_model('profiles', 'Profile')
    for row in Profile.objects.all():
        row.authentication_identifier = row.email
        row.save()


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0020_auto_20151013_0506'),
    ]

    operations = [
        migrations.RunPython(
            default_authentication_identifier_to_email,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
