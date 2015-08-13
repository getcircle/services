import json

from django.db import connection
from protobufs.services.history import containers_pb2 as history_containers


def action_container(instance, field_name, new_value, action_type, method_type):
    primary_key = instance._meta.pk
    primary_key_name = primary_key.db_column or primary_key.column
    primary_key_value = instance.pk
    field = instance._meta._forward_fields_map[field_name]
    table_name = instance._meta.db_table
    column_name = field.db_column or field.column
    data_type = field.db_type(connection)
    old_value = getattr(instance, field_name)
    kwargs = {
        'table_name': table_name,
        'column_name': column_name,
        'data_type': data_type,
        'action_type': action_type,
        'method_type': method_type,
        'primary_key_name': primary_key_name,
        'primary_key_value': str(primary_key_value),
    }

    if old_value is not None:
        if isinstance(old_value, dict):
            old_value = json.dumps(old_value)
        kwargs['old_value'] = old_value

    if new_value is not None:
        if isinstance(new_value, dict):
            new_value = json.dumps(new_value)
        kwargs['new_value'] = new_value

    return history_containers.ActionV1(**kwargs)


def action_container_for_update(instance, field_name, new_value, action_type):
    return action_container(
        instance=instance,
        field_name=field_name,
        new_value=new_value,
        action_type=action_type,
        method_type=history_containers.UPDATE,
    )


def action_container_for_delete(instance, field_name, action_type):
    return action_container(
        instance=instance,
        field_name=field_name,
        action_type=action_type,
        method_type=history_containers.DELETE,
        new_value=None,
    )
