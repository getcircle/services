# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import bitfield.models
import protobufs.services.notification.containers_pb2
import uuid


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='NotificationPreference',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, serialize=False, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('changed', models.DateTimeField(auto_now=True)),
                ('profile_id', models.UUIDField()),
                ('subscribed', models.BooleanField()),
            ],
            options={
                'protobuf': protobufs.services.notification.containers_pb2.NotificationPreferenceV1,
            },
        ),
        migrations.CreateModel(
            name='NotificationToken',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, serialize=False, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('changed', models.DateTimeField(auto_now=True)),
                ('user_id', models.UUIDField()),
                ('device_id', models.UUIDField()),
                ('provider_token', models.CharField(max_length=255)),
                ('provider', models.SmallIntegerField(choices=[(0, b'SNS'), (1, b'GMS')])),
            ],
            options={
                'protobuf': protobufs.services.notification.containers_pb2.NotificationTokenV1,
            },
        ),
        migrations.CreateModel(
            name='NotificationType',
            fields=[
                ('created', models.DateTimeField(auto_now_add=True)),
                ('changed', models.DateTimeField(auto_now=True)),
                ('id', models.SmallIntegerField(serialize=False, primary_key=True, choices=[(0, b'GROUP_MEMBERSHIP_REQUEST'), (1, b'UPCOMING_BIRTHDAY_TEAM')])),
                ('description', models.CharField(max_length=255)),
                ('channels', bitfield.models.BitField((b'mobile_push',), default=None)),
                ('opt_in', models.BooleanField(default=False)),
            ],
            options={
                'protobuf': protobufs.services.notification.containers_pb2.NotificationTypeV1,
            },
        ),
        migrations.AlterIndexTogether(
            name='notificationtoken',
            index_together=set([('user_id', 'provider')]),
        ),
        migrations.AddField(
            model_name='notificationpreference',
            name='notification_type',
            field=models.ForeignKey(to='notification.NotificationType'),
        ),
        migrations.AlterIndexTogether(
            name='notificationpreference',
            index_together=set([('profile_id', 'notification_type', 'subscribed')]),
        ),
    ]
