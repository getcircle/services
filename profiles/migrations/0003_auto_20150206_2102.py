# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0002_auto_20150117_0620'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='ProfileTags',
            new_name='ProfileSkills',
        ),
        migrations.RenameModel(
            old_name='Tag',
            new_name='Skill',
        ),
        migrations.RenameField(
            model_name='profileskills',
            old_name='tag',
            new_name='skill',
        ),
        migrations.RemoveField(
            model_name='profile',
            name='tags',
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
    ]
