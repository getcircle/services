# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import services.fields
import timezone_field.fields
import mptt.fields
import django.contrib.postgres.fields
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0028_auto_20150812_0033'),
    ]

    operations = [
        migrations.CreateModel(
            name='Location',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, serialize=False, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('changed', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=64)),
                ('address_1', models.CharField(max_length=128)),
                ('address_2', models.CharField(max_length=128, null=True)),
                ('city', models.CharField(max_length=64)),
                ('region', models.CharField(max_length=64)),
                ('postal_code', models.CharField(max_length=64)),
                ('country_code', models.CharField(max_length=3)),
                ('latitude', models.DecimalField(max_digits=10, decimal_places=6)),
                ('longitude', models.DecimalField(max_digits=10, decimal_places=6)),
                ('timezone', timezone_field.fields.TimeZoneField()),
                ('image_url', models.URLField(max_length=255, null=True)),
                ('description', services.fields.DescriptionField(null=True)),
                ('established_date', models.DateField(null=True)),
                ('points_of_contact_profile_ids', django.contrib.postgres.fields.ArrayField(null=True, base_field=models.UUIDField(), size=None)),
                ('organization', models.ForeignKey(editable=False, to='organizations.Organization')),
            ],
        ),
        migrations.CreateModel(
            name='LocationMember',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, serialize=False, primary_key=True)),
                ('profile_id', models.UUIDField()),
                ('added_by_profile_id', models.UUIDField(null=True, editable=False)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('location', models.ForeignKey(related_name='members', to='organizations.Location')),
                ('organization', models.ForeignKey(editable=False, to='organizations.Organization')),
            ],
        ),
        migrations.CreateModel(
            name='ReportingStructure',
            fields=[
                ('created', models.DateTimeField(auto_now_add=True)),
                ('changed', models.DateTimeField(auto_now=True)),
                ('profile_id', models.UUIDField(serialize=False, primary_key=True)),
                ('added_by_profile_id', models.UUIDField(null=True, editable=False)),
                ('lft', models.PositiveIntegerField(editable=False, db_index=True)),
                ('rght', models.PositiveIntegerField(editable=False, db_index=True)),
                ('tree_id', models.PositiveIntegerField(editable=False, db_index=True)),
                ('level', models.PositiveIntegerField(editable=False, db_index=True)),
                ('manager', mptt.fields.TreeForeignKey(related_name='reports', to='organizations.ReportingStructure', null=True)),
                ('organization', models.ForeignKey(editable=False, to='organizations.Organization')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Team',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, serialize=False, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('changed', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=255, null=True)),
                ('description', services.fields.DescriptionField(null=True)),
                ('manager_profile_id', models.UUIDField(editable=False)),
                ('created_by_profile_id', models.UUIDField(editable=False)),
                ('image_url', models.URLField(max_length=255, null=True)),
                ('organization', models.ForeignKey(editable=False, to='organizations.Organization')),
            ],
        ),
        migrations.CreateModel(
            name='TeamStatus',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, serialize=False, primary_key=True)),
                ('value', models.TextField(null=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('organization_id', models.UUIDField(editable=False)),
                ('by_profile_id', models.UUIDField(editable=False)),
                ('team', models.ForeignKey(to='organizations.Team')),
            ],
        ),
        migrations.AlterIndexTogether(
            name='teamstatus',
            index_together=set([('team', 'organization_id', 'created')]),
        ),
        migrations.AlterIndexTogether(
            name='team',
            index_together=set([('manager_profile_id', 'organization')]),
        ),
        migrations.AlterIndexTogether(
            name='locationmember',
            index_together=set([('location', 'organization'), ('profile_id', 'organization')]),
        ),
        migrations.AlterUniqueTogether(
            name='location',
            unique_together=set([('name', 'organization')]),
        ),
    ]
