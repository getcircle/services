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
                ('organization_id', models.UUIDField()),
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
                ('provider', models.SmallIntegerField(choices=[(0, b'SNS')])),
                ('provider_platform', models.SmallIntegerField(null=True, choices=[(0, b'APNS'), (1, b'GCM')])),
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
                ('id', models.SmallIntegerField(serialize=False, primary_key=True, choices=[(0, b'GOOGLE_GROUPS')])),
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
            field=models.ForeignKey(related_name='preferences', to='notification.NotificationType'),
        ),
        migrations.AlterUniqueTogether(
            name='notificationpreference',
            unique_together=set([('profile_id', 'notification_type')]),
        ),
        migrations.AlterIndexTogether(
            name='notificationpreference',
            index_together=set([('profile_id', 'notification_type', 'subscribed')]),
        ),
    ]
