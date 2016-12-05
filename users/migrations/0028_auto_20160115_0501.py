# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


def populate_organization_id(apps, schema_editor):
    User = apps.get_model('users', 'User')
    Profile = apps.get_model('profiles', 'Profile')
    profile_dict = dict((p.user_id, p) for p in Profile.objects.all())
    user_dict = {}
    for user in User.objects.all():
        profile = profile_dict.get(user.id)
        if profile:
            user.organization_id = profile.organization_id
            user.save()
            user_dict[user.id] = user
        else:
            print 'deleting user: %s' % (user.__dict__,)
            user.delete()

    Device = apps.get_model('users', 'Device')
    for device in Device.objects.all():
        user = user_dict.get(device.user_id)
        if user:
            device.organization_id = user.organization_id
            device.save()
        else:
            print 'deleting device: %s' % (device.__dict__,)
            device.delete()

    Identity = apps.get_model('users', 'Identity')
    for identity in Identity.objects.all():
        user = user_dict.get(identity.user_id)
        if user:
            identity.organization_id = user.organization_id
            identity.save()
        else:
            print 'deleting identity: %s' % (identity.__dict__,)
            identity.delete()

    Token = apps.get_model('users', 'Token')
    for token in Token.objects.all():
        user = user_dict.get(token.user_id)
        if user:
            token.organization_id = user.organization_id
            token.save()
        else:
            print 'deleting token: %s' % (token.__dict__,)
            token.delete()

    TOTPToken = apps.get_model('users', 'TOTPToken')
    for token in TOTPToken.objects.all():
        user = user_dict.get(token.user_id)
        if user:
            token.organization_id = user.organization_id
            token.save()
        else:
            print 'deleting token: %s' % (token.__dict__,)
            token.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0027_auto_20160115_0501'),
        ('profiles', '0026_auto_20160120_1748'),
    ]

    operations = [
        migrations.RunPython(populate_organization_id, reverse_code=migrations.RunPython.noop),
    ]
