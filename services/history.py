import json

from django.db import connection
from protobuf_to_dict import protobuf_to_dict
from protobufs.services.history import containers_pb2 as history_containers


def action_container(instance, method_type, field_name=None, new_value=None, action_type=None):
    primary_key = instance._meta.pk
    primary_key_name = primary_key.db_column or primary_key.column
    primary_key_value = instance.pk
    table_name = instance._meta.db_table

    column_name = None
    data_type = None
    old_value = None
    if field_name:
        field = instance._meta._forward_fields_map[field_name]
        column_name = field.db_column or field.column
        data_type = field.db_type(connection)
        old_value = getattr(instance, field_name)
        if hasattr(old_value, 'SerializeToString'):
            old_value = protobuf_to_dict(old_value)

    if hasattr(new_value, 'SerializeToString'):
        new_value = protobuf_to_dict(new_value)

    kwargs = {
        'table_name': table_name,
        'method_type': method_type,
        'primary_key_name': primary_key_name,
        'primary_key_value': str(primary_key_value),
    }

    if action_type is not None:
        kwargs['action_type'] = action_type

    if old_value is not None:
        if isinstance(old_value, dict):
            old_value = json.dumps(old_value)
        else:
            old_value = str(old_value)
        kwargs['old_value'] = old_value

    if data_type is not None:
        kwargs['data_type'] = data_type

    if column_name is not None:
        kwargs['column_name'] = column_name

    if new_value is not None:
        if isinstance(new_value, dict):
            new_value = json.dumps(new_value)
        else:
            new_value = str(new_value)
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


def action_container_for_create(instance):
    return action_container(
        instance=instance,
        method_type=history_containers.CREATE,
        action_type=history_containers.CREATE_INSTANCE,
        new_value=None,
    )
