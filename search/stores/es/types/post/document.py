from elasticsearch_dsl import (
    analyzer,
    Date,
    Integer,
    MetaField,
    String,
)
from protobufs.services.post import containers_pb2 as post_containers

from ...analysis import (
    edge_ngram_max_gram_20,
    raw_search,
    shingle_filter,
    shingle_search,
)
from ..base import BaseDocType


title_analyzer_v1 = analyzer(
    'post_title_analyzer_v1',
    tokenizer='standard',
    filter=['standard', 'lowercase', edge_ngram_max_gram_20],
)

title_shingle_analyzer_v1 = analyzer(
    'post_title_shingle_analyzer_v1',
    tokenizer='standard',
    filter=['standard', 'lowercase', shingle_filter],
)

raw_analyzer_v1 = analyzer(
    'post_raw_analyzer_v1',
    tokenizer='keyword',
    filter=['standard', 'lowercase'],
)

stem_analyzer_v1 = analyzer(
    'post_stem_analyzer_v1',
    tokenizer='standard',
    filter=['standard', 'lowercase', 'kstem'],
)


class PostV1(BaseDocType):
    title = String(
        analyzer=title_analyzer_v1,
        fields={
            'shingle': String(
                analyzer=title_shingle_analyzer_v1,
                search_analyzer=shingle_search,
            ),
            'stemmed': String(analyzer=stem_analyzer_v1),
            'raw': String(analyzer=raw_analyzer_v1, search_analyzer=raw_search),
        },
        search_analyzer='default_search',
    )
    content = String(
        analyzer='english',
        fields={
            'stemmed': String(analyzer=stem_analyzer_v1),
            'raw': String(analyzer=raw_analyzer_v1, search_analyzer=raw_search),
        },
    )
    state = Integer()
    created = Date()
    changed = Date()
    organization_id = String(index='not_analyzed')

    class Meta:
        doc_type = 'post'
        all = MetaField(enabled=False)
        dynamic = MetaField('false')
        protobuf = post_containers.PostV1
