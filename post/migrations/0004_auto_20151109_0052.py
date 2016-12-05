# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('post', '0003_attachment'),
    ]

    operations = [
        migrations.AlterField(
            model_name='attachment',
            name='post',
            field=models.ForeignKey(related_name='attachments', to='post.Post'),
        ),
    ]
