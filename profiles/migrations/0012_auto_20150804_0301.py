# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import protobufs.services.profile.containers_pb2
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0011_remove_profile_about'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProfileStatus',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, serialize=False, primary_key=True)),
                ('value', models.TextField(null=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('organization_id', models.UUIDField()),
                ('profile', models.ForeignKey(to='profiles.Profile')),
            ],
            options={
                'protobuf': protobufs.services.profile.containers_pb2.ProfileStatusV1,
            },
        ),
        migrations.AlterIndexTogether(
            name='profilestatus',
            index_together=set([('profile', 'organization_id', 'created')]),
        ),
    ]
