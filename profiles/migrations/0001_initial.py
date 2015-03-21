# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.contrib.postgres.fields
import phonenumber_field.modelfields
import uuid


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Profile',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, serialize=False, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('changed', models.DateTimeField(auto_now=True)),
                ('organization_id', models.UUIDField()),
                ('user_id', models.UUIDField()),
                ('address_id', models.UUIDField(null=True, db_index=True)),
                ('location_id', models.UUIDField(null=True, db_index=True)),
                ('team_id', models.UUIDField(db_index=True)),
                ('title', models.CharField(max_length=255)),
                ('first_name', models.CharField(max_length=64)),
                ('last_name', models.CharField(max_length=64)),
                ('cell_phone', phonenumber_field.modelfields.PhoneNumberField(max_length=128, null=True)),
                ('work_phone', phonenumber_field.modelfields.PhoneNumberField(max_length=128, null=True)),
                ('image_url', models.URLField(max_length=256, null=True)),
                ('email', models.EmailField(max_length=254)),
                ('birth_date', models.DateField()),
                ('hire_date', models.DateField()),
                ('verified', models.BooleanField(default=False)),
                ('items', django.contrib.postgres.fields.ArrayField(null=True, base_field=django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=256, null=True), size=2), size=None)),
                ('about', models.TextField(null=True)),
            ],
        ),
        migrations.CreateModel(
            name='ProfileSkills',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('changed', models.DateTimeField(auto_now=True)),
                ('profile', models.ForeignKey(to='profiles.Profile')),
            ],
        ),
        migrations.CreateModel(
            name='Skill',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, serialize=False, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('changed', models.DateTimeField(auto_now=True)),
                ('organization_id', models.UUIDField(db_index=True)),
                ('name', models.CharField(max_length=64)),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='skill',
            unique_together=set([('organization_id', 'name')]),
        ),
        migrations.AddField(
            model_name='profileskills',
            name='skill',
            field=models.ForeignKey(to='profiles.Skill'),
        ),
        migrations.AddField(
            model_name='profile',
            name='skills',
            field=models.ManyToManyField(to='profiles.Skill', through='profiles.ProfileSkills'),
        ),
        migrations.AlterUniqueTogether(
            name='profileskills',
            unique_together=set([('skill', 'profile')]),
        ),
        migrations.AlterUniqueTogether(
            name='profile',
            unique_together=set([('organization_id', 'user_id')]),
        ),
    ]
