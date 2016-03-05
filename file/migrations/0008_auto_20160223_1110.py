# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import urllib

from django.db import models, migrations


def source_url_to_key(apps, schema_editor):
    File = apps.get_model('file', 'File')
    for row in File.objects.all():
        row.key = urllib.unquote(row.source_url.rsplit('/', 1)[1])
        row.save()


class Migration(migrations.Migration):

    dependencies = [
        ('file', '0007_auto_20160223_1109'),
    ]

    operations = [
        migrations.RunPython(source_url_to_key, reverse_code=migrations.RunPython.noop),
    ]
