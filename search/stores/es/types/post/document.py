from elasticsearch_dsl import (
    analyzer,
    Date,
    Integer,
    MetaField,
    String,
)
from protobufs.services.post import containers_pb2 as post_containers

from ...indices import search_v1
from ...analysis import edge_ngram_max_gram_20
from ..base import BaseDocType


title_analyzer_v1 = analyzer(
    'post_title_analyzer_v1',
    tokenizer='standard',
    filter=['standard', 'lowercase', edge_ngram_max_gram_20],
)


@search_v1.INDEX.doc_type
class PostV1(BaseDocType):
    title = String(analyzer=title_analyzer_v1)
    content = String()
    state = Integer()
    created = Date()
    changed = Date()
    organization_id = String(index='not_analyzed')

    class Meta:
        doc_type = 'post'
        all = MetaField(enabled=False)
        dynamic = MetaField('false')
        protobuf = post_containers.PostV1