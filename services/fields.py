from django.contrib.postgres.fields import HStoreField
from protobuf_to_dict import (
    dict_to_protobuf,
    protobuf_to_dict,
)

from protobufs.services.common import containers_pb2 as common_containers


class DescriptionField(HStoreField):

    def to_python(self, value):
        value = super(DescriptionField, self).to_python(value)
        if value is None or hasattr(value, 'SerializeToString'):
            return value
        return dict_to_protobuf(value, common_containers.DescriptionV1)

    def get_prep_value(self, value):
        if value is None:
            return value
        output = protobuf_to_dict(value)
        output.pop('by_profile', None)
        return output

    def as_dict_value_transform(self, value):
        if value is None:
            return value
        return protobuf_to_dict(value)
