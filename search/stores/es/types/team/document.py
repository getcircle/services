from elasticsearch_dsl import (
    analyzer,
    MetaField,
    String,
)
from protobufs.services.organization import containers_pb2 as organization_containers

from ...analysis import edge_ngram_max_gram_20
from ..base import BaseDocType


name_analyzer_v1 = analyzer(
    'team_name_analyzer_v1',
    tokenizer='standard',
    filter=['standard', 'lowercase', edge_ngram_max_gram_20],
)


class TeamV1(BaseDocType):
    name = String(analyzer=name_analyzer_v1, search_analyzer='default_search')
    description = String(analyzer='english')

    class Meta:
        doc_type = 'team'
        all = MetaField(enabled=False)
        dynamic = MetaField('false')
        protobuf = organization_containers.TeamV1
