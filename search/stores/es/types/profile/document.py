from elasticsearch_dsl import (
    MetaField,
    String,
)
from protobufs.services.profile import containers_pb2 as profile_containers

from ...indices import search_v1
from ..base import BaseDocType
from . import analysis


@search_v1.INDEX.doc_type
class ProfileV1(BaseDocType):
    email = String()
    full_name = String(index_analyzer=analysis.full_name_analyzer_v1)
    display_title = String(index_analyzer=analysis.display_title_analyzer_v1)
    organization_id = String(index='not_analyzed')

    class Meta:
        doc_type = 'profile'
        all = MetaField(enabled=False)
        # don't index dynamic fields
        dynamic = MetaField('false')
        protobuf = profile_containers.ProfileV1
