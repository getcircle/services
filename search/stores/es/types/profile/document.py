from elasticsearch_dsl import DocType, String, MetaField
from protobuf_to_dict import (
    dict_to_protobuf,
    protobuf_to_dict,
)
from protobufs.services.profile import containers_pb2 as profile_containers

from ...indices import search_v1
from . import analysis


@search_v1.INDEX.doc_type
class ProfileV1(DocType):
    full_name = String(analyzer=analysis.full_name_analyzer_v1)
    email = String()
    display_title = String(analyzer=analysis.display_title_analyzer_v1)

    @classmethod
    def from_protobuf(cls, protobuf):
        return cls(_id=protobuf.id, **protobuf_to_dict(protobuf))

    def to_protobuf(self):
        return dict_to_protobuf(self.to_dict(), profile_containers.ProfileV1, strict=False)

    class Meta:
        doc_type = 'profile'
        all = MetaField(enabled=False)
        # don't index dynamic fields
        dynamic = MetaField('false')
