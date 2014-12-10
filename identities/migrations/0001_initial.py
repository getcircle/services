# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import phonenumber_field.modelfields


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_auto_20141210_0355'),
    ]

    operations = [
        migrations.CreateModel(
            name='Identity',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('changed', models.DateTimeField(auto_now=True)),
                ('first_name', models.CharField(max_length=64)),
                ('last_name', models.CharField(max_length=64)),
                ('email', models.EmailField(max_length=75)),
                ('phone_number', phonenumber_field.modelfields.PhoneNumberField(max_length=128, null=True)),
                ('user', models.ForeignKey(to='users.User')),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
    ]
