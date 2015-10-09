# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


def set_changed_to_created(apps, schema_editor):
    TeamStatus = apps.get_model('organizations', 'TeamStatus')
    for row in TeamStatus.objects.all():
        TeamStatus.objects.filter(pk=row.pk).update(changed=row.created)


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0034_teamstatus_changed'),
    ]

    operations = [
        migrations.RunPython(set_changed_to_created, reverse_code=migrations.RunPython.noop),
    ]
