# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


def populate_organization_id(apps, schema_editor):
    User = apps.get_model('users', 'User')
    Profile = apps.get_model('profiles', 'Profile')
    profile_dict = dict((p.user_id, p) for p in Profile.objects.all())
    user_dict = {}
    for user in User.objects.all():
        profile = profile_dict[user.id]
        user.organization_id = profile.organization_id
        user.save()
        user_dict[user.id] = user

    Device = apps.get_model('users', 'Device')
    for device in Device.objects.all():
        user = user_dict[device.user_id]
        device.organization_id = user.organization_id
        device.save()

    Identity = apps.get_model('users', 'Identity')
    for identity in Identity.objects.all():
        user = user_dict[identity.user_id]
        identity.organization_id = user.organization_id
        identity.save()

    Token = apps.get_model('users', 'Token')
    for token in Token.objects.all():
        user = user_dict[token.user_id]
        token.organization_id = user.organization_id
        token.save()

    TOTPToken = apps.get_model('users', 'TOTPToken')
    for token in TOTPToken.objects.all():
        user = user_dict[token.user_id]
        token.organization_id = user.organization_id
        token.save()


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0027_auto_20160115_0501'),
        ('profiles', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(populate_organization_id, reverse_code=migrations.RunPython.noop),
    ]
