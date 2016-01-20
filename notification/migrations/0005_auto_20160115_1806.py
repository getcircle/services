# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


def populate_organization_id(apps, schema_editor):
    User = apps.get_model('users', 'User')
    user_dict = dict((u.id, u) for u in User.objects.all())

    NotificationToken = apps.get_model('notification', 'NotificationToken')
    for token in NotificationToken.objects.all():
        user = user_dict[token.user_id]
        token.organization_id = user.organization_id
        token.save()


class Migration(migrations.Migration):

    dependencies = [
        ('notification', '0004_notificationtoken_organization_id'),
        ('users', '0029_auto_20160115_0501'),
    ]

    operations = [
        migrations.RunPython(populate_organization_id, reverse_code=migrations.RunPython.noop),
    ]
