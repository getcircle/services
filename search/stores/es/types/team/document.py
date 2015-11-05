from elasticsearch_dsl import (
    analyzer,
    MetaField,
    String,
)
from protobufs.services.organization import containers_pb2 as organization_containers

from ...analysis import (
    edge_ngram_max_gram_20,
    parens_strip,
)
from ...indices import search_v1
from ..base import BaseDocType


name_analyzer_v1 = analyzer(
    'team_name_analyzer_v1',
    tokenizer='standard',
    filter=['standard', 'lowercase', edge_ngram_max_gram_20],
    char_filter=[parens_strip],
)


@search_v1.INDEX.doc_type
class TeamV1(BaseDocType):
    name = String(analyzer=name_analyzer_v1, search_analyzer='default_search')
    description = String(analyzer='english')
    organization_id = String(index='not_analyzed')

    class Meta:
        doc_type = 'team'
        all = MetaField(enabled=False)
        dynamic = MetaField('false')
        protobuf = organization_containers.TeamV1
