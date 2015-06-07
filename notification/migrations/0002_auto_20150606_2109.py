# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from protobufs.services.notification import containers_pb2 as notification_containers


def new_notification(apps, schema_editor):
    NotificationType = apps.get_model('notification', 'NotificationType')
    notification = NotificationType.objects.create(
        id=notification_containers.NotificationTypeV1.GROUP_MEMBERSHIP_REQUEST,
        description='Group membership requests',
        channels=0,
        opt_in=False,
    )
    NotificationType.objects.filter(
        id=notification.id
    ).update(channels=NotificationType.channels.mobile_push)


class Migration(migrations.Migration):

    dependencies = [
        ('notification', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(new_notification),
    ]
