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
    full_name = String(analyzer=analysis.full_name_analyzer_v1, search_analyzer='default_search')
    email = String(analyzer=analysis.email_analyzer_v1, search_analyzer='default_search')
    display_title = String(
        analyzer=analysis.display_title_analyzer_v1,
        search_analyzer='default_search',
    )
    organization_id = String(index='not_analyzed')

    class Meta:
        doc_type = 'profile'
        all = MetaField(enabled=False)
        # don't index dynamic fields
        dynamic = MetaField('false')
        protobuf = profile_containers.ProfileV1
