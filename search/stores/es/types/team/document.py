from elasticsearch_dsl import (
    MetaField,
    String,
)
from protobufs.services.organization import containers_pb2 as organization_containers

from ...indices import search_v1
from ..base import BaseDocType
from . import analysis


@search_v1.INDEX.doc_type
class TeamV1(BaseDocType):
    name = String(analyzer=analysis.name_analyzer_v1)
    description = String(analyzer='english')
    organization_id = String(index='not_analyzed')

    class Meta:
        doc_type = 'team'
        all = MetaField(enabled=False)
        dynamic = MetaField('false')
        protobuf = organization_containers.TeamV1
