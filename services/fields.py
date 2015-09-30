from django.contrib.postgres.fields import HStoreField
from protobuf_to_dict import (
    dict_to_protobuf,
    protobuf_to_dict,
)

from protobufs.services.common import containers_pb2 as common_containers


# TODO we should be using JSONField when postgres 1.9 is released. i know its
# ironic we're storing protobuf value in JSON, but its more human readable in
# the db.
class DescriptionField(HStoreField):

    def _to_protobuf(self, value):
        if value is None or hasattr(value, 'SerializeToString'):
            return value
        if value.get('version') and isinstance(value['version'], basestring):
            value['version'] = int(value['version'])
        return dict_to_protobuf(value, common_containers.DescriptionV1)

    def from_db_value(self, value, expression, connection, context):
        return self._to_protobuf(value)

    def to_python(self, value):
        value = super(DescriptionField, self).to_python(value)
        return self._to_protobuf(value)

    def get_prep_value(self, value):
        if value is None:
            return value
        output = protobuf_to_dict(value)
        output.pop('by_profile', None)
        if output.get('version'):
            output['version'] = str(output['version'])
        return output

    def as_dict_value_transform(self, value):
        if value is None:
            return value
        return protobuf_to_dict(value)
