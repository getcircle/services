# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


def set_changed_to_created(apps, schema_editor):
    ProfileStatus = apps.get_model('profiles', 'ProfileStatus')
    for row in ProfileStatus.objects.all():
        ProfileStatus.objects.filter(pk=row.pk).update(changed=row.created)


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0017_profilestatus_changed'),
    ]

    operations = [
        migrations.RunPython(set_changed_to_created, reverse_code=migrations.RunPython.noop),
    ]
