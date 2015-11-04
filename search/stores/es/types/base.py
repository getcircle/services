from elasticsearch_dsl import DocType
from elasticsearch_dsl.document import DocTypeMeta
from protobuf_to_dict import (
    dict_to_protobuf,
    protobuf_to_dict,
)
from six import add_metaclass


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
            for key, value in cls.document_to_protobuf_mapping.iteritems():
                data[key] = data.pop(value, None)
        return cls(_id=protobuf.id, **data)

    @classmethod
    def prepare_protobuf_dict(cls, data):
        if cls.document_to_protobuf_mapping:
            for key, value in cls.document_to_protobuf_mapping.iteritems():
                data[value] = data.pop(key, None)

    def to_protobuf(self):
        data = self.to_dict()
        self.prepare_protobuf_dict(data)
        return dict_to_protobuf(data, self._options.protobuf, strict=False)
