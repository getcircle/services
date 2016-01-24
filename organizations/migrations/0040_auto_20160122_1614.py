# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from protobufs.services.organization.containers import sso_pb2


def migrate_to_details(apps, schema_editor):
    SSO = apps.get_model('organizations', 'SSO')
    for sso in SSO.objects.all():
        saml = sso_pb2.SAMLDetailsV1(config_url=sso.metadata_url, config=sso.metadata)
        sso.details = saml
        sso.save()


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0039_auto_20160122_0122'),
    ]

    operations = [
        migrations.RunPython(migrate_to_details, reverse_code=migrations.RunPython.noop),
    ]
