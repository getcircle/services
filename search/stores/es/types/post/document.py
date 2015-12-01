from elasticsearch_dsl import (
    analyzer,
    Date,
    Integer,
    MetaField,
    String,
)
from protobufs.services.post import containers_pb2 as post_containers

from ...analysis import (
    edge_ngram_tokenizer_v1,
    shingle_filter,
    shingle_search,
)
from ..base import BaseDocType


title_analyzer_v1 = analyzer(
    'post_title_analyzer_v1',
    tokenizer=edge_ngram_tokenizer_v1,
    filter=['standard', 'lowercase'],
)

title_shingle_analyzer_v1 = analyzer(
    'post_title_shingle_analyzer_v1',
    tokenizer='standard',
    filter=['standard', 'lowercase', shingle_filter],
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
                term_vector='with_positions_offsets',
            ),
            'stemmed': String(
                analyzer=stem_analyzer_v1,
                term_vector='with_positions_offsets',
            ),
        },
        search_analyzer='default_search',
        term_vector='with_positions_offsets',
    )
    content = String(analyzer='english')
    state = Integer()
    created = Date()
    changed = Date()

    class Meta:
        doc_type = 'post'
        all = MetaField(enabled=False)
        dynamic = MetaField('false')
        protobuf = post_containers.PostV1
