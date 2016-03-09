# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class CollectionDeferredUniqueTogether(migrations.AlterUniqueTogether):

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        new_model = to_state.apps.get_model(app_label, self.name)
        if self.allow_migrate_model(schema_editor.connection.alias, new_model):
            statement = schema_editor._create_unique_sql(
                new_model,
                ('organization_id', 'owner_id', 'owner_type', 'position'),
            )
            statement += ' INITIALLY DEFERRED'
            schema_editor.execute(statement)

class Migration(migrations.Migration):

    dependencies = [
        ('post', '0011_auto_20160228_2330'),
    ]

    operations = [
        migrations.AddField(
            model_name='collection',
            name='position',
            field=models.PositiveSmallIntegerField(null=True),
        ),
        migrations.AlterUniqueTogether(
            name='collection',
            unique_together=set([('organization_id', 'owner_id', 'owner_type', 'is_default')]),
        ),
        CollectionDeferredUniqueTogether(
            name='collection',
            unique_together=set([('organization_id', 'owner_id', 'owner_type', 'position')]),
        ),
    ]
