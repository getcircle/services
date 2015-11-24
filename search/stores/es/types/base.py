from collections import namedtuple

from elasticsearch_dsl import DocType
from elasticsearch_dsl.document import DocTypeMeta
from protobuf_to_dict import (
    dict_to_protobuf,
    protobuf_to_dict,
)
from six import add_metaclass


HighlightField = namedtuple('HightField', ('field_name', 'options'))


def _get_nested_value(path, data):
    if '.' not in path:
        return data.pop(path, None)

    part, path = path.split('.', 1)
    if part not in data:
        return None

    return _get_nested_value(path, data.pop(part))


def _set_nested_value(path, data, value):
    if '.' not in path:
        data[path] = value
        return

    part, path = path.split('.', 1)
    data[part] = {}
    _set_nested_value(path, data[part], value)


class Options(object):

    def __init__(self, protobuf):
        self.protobuf = protobuf


class BaseDocTypeMeta(DocTypeMeta):

    def __new__(cls, name, bases, attrs):
        meta = attrs.get('Meta')
        attrs['_options'] = Options(protobuf=getattr(meta, 'protobuf', None))
        return super(BaseDocTypeMeta, cls).__new__(cls, name, bases, attrs)


@add_metaclass(BaseDocTypeMeta)
class BaseDocType(DocType):

    document_to_protobuf_mapping = None

    @classmethod
    def from_protobuf(cls, protobuf):
        data = protobuf_to_dict(protobuf)
        if cls.document_to_protobuf_mapping:
            for field_name, proto_field_name in cls.document_to_protobuf_mapping.iteritems():
                if isinstance(proto_field_name, DocumentToProtobufOptions):
                    if not proto_field_name.on_from_protobuf:
                        proto_field_name = field_name
                    else:
                        proto_field_name = proto_field_name.field_name

                value = _get_nested_value(proto_field_name, data)
                if value is not None:
                    data[field_name] = value

        return cls(_id=protobuf.id, **data)

    @classmethod
    def prepare_protobuf_dict(cls, data):
        if cls.document_to_protobuf_mapping:
            for field_name, proto_field_name in cls.document_to_protobuf_mapping.iteritems():
                action = 'pop'
                if isinstance(proto_field_name, DocumentToProtobufOptions):
                    if not proto_field_name.replace:
                        action = 'get'
                    proto_field_name = proto_field_name.field_name

                value = getattr(data, action)(field_name, None)
                if value is not None:
                    _set_nested_value(proto_field_name, data, value)

    @classmethod
    def prepare_highlight_dict(cls, data):
        if cls.document_to_protobuf_mapping:
            for field_name, proto_field_name in cls.document_to_protobuf_mapping.iteritems():
                action = 'pop'
                if isinstance(proto_field_name, DocumentToProtobufOptions):
                    if not proto_field_name.replace:
                        action = 'get'

                    if not proto_field_name.on_prepare_highlight_dict:
                        proto_field_name = field_name
                    else:
                        proto_field_name = proto_field_name.field_name

                value = getattr(data, action)(field_name, None)
                if value is not None:
                    _set_nested_value(proto_field_name, data, value)

    def to_protobuf(self):
        data = self.to_dict()
        self.prepare_protobuf_dict(data)
        return dict_to_protobuf(data, self._options.protobuf, strict=False)


class DocumentToProtobufOptions(object):

    def __init__(
            self,
            field_name,
            on_from_protobuf=True,
            replace=True,
            on_prepare_highlight_dict=True,
        ):
        """Options for translating fields from ES document to protobuf.

        Args:
            field_name (str): protobuf field name we're translating to.
            on_from_protobuf (Optional[bool]): allows us to specify that the
                mapping should only be applied when exporting values, ie.
                document -> protobuf, not protobuf
            replace (Optional[bool]): whether or not we should replace the
                field_name within the ES document.
            on_prepare_highlight_dict (Optional[bool]): allows us to disable
                translations when preparing the highlight dict. This is useful
                when dealing with nested fields like "description.value". The
                highlighter doesn't support nested fields, so this should just
                be left as "description".

        """
        self.field_name = field_name
        self.on_from_protobuf = on_from_protobuf
        self.replace = replace
        self.on_prepare_highlight_dict = on_prepare_highlight_dict
