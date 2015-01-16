# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import phonenumber_field.modelfields
import uuid


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Profile',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, max_length=32, serialize=False, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('changed', models.DateTimeField(auto_now=True)),
                ('organization_id', models.UUIDField(max_length=32)),
                ('user_id', models.UUIDField(max_length=32)),
                ('address_id', models.UUIDField(max_length=32)),
                ('team_id', models.UUIDField(max_length=32)),
                ('title', models.CharField(max_length=64)),
                ('first_name', models.CharField(max_length=64)),
                ('last_name', models.CharField(max_length=64)),
                ('cell_phone', phonenumber_field.modelfields.PhoneNumberField(max_length=128, null=True)),
                ('work_phone', phonenumber_field.modelfields.PhoneNumberField(max_length=128, null=True)),
                ('image_url', models.CharField(max_length=256, null=True)),
                ('email', models.EmailField(max_length=254)),
                ('birth_date', models.DateField()),
                ('hire_date', models.DateField()),
                ('verified', models.BooleanField(default=False)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ProfileTags',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('changed', models.DateTimeField(auto_now=True)),
                ('profile', models.ForeignKey(to='profiles.Profile')),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Tag',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, max_length=32, serialize=False, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('changed', models.DateTimeField(auto_now=True)),
                ('organization_id', models.UUIDField(max_length=32, db_index=True)),
                ('name', models.CharField(max_length=64)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='tag',
            unique_together=set([('organization_id', 'name')]),
        ),
        migrations.AddField(
            model_name='profiletags',
            name='tag',
            field=models.ForeignKey(to='profiles.Tag'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='profile',
            name='tags',
            field=models.ManyToManyField(to='profiles.Tag', through='profiles.ProfileTags'),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='profile',
            unique_together=set([('organization_id', 'user_id')]),
        ),
    ]
