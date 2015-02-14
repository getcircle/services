# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import uuid


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Company',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, max_length=32, serialize=False, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('changed', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=255)),
                ('linkedin_id', models.CharField(max_length=255, null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Education',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, max_length=32, serialize=False, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('changed', models.DateTimeField(auto_now=True)),
                ('user_id', models.UUIDField(max_length=32)),
                ('school_name', models.CharField(max_length=255)),
                ('start_date', models.DateField(null=True)),
                ('end_date', models.DateField(null=True)),
                ('notes', models.TextField(null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Position',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, max_length=32, serialize=False, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('changed', models.DateTimeField(auto_now=True)),
                ('user_id', models.UUIDField(max_length=32)),
                ('title', models.CharField(max_length=255)),
                ('start_date', models.DateField(null=True)),
                ('end_date', models.DateField(null=True)),
                ('summary', models.TextField(null=True)),
                ('company', models.ForeignKey(to='resumes.Company', null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
