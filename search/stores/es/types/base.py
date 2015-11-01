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

    @classmethod
    def from_protobuf(cls, protobuf):
        return cls(_id=protobuf.id, **protobuf_to_dict(protobuf))

    def to_protobuf(self):
        return dict_to_protobuf(self.to_dict(), self._options.protobuf, strict=False)
