from elasticsearch_dsl import (
    analyzer,
    MetaField,
    String,
)
from protobufs.services.post import containers_pb2 as post_containers

from ...analysis import (
    edge_ngram_tokenizer_v1,
    raw_analyzer_v1,
    raw_search,
)

from ..base import BaseDocType

name_analyzer_v1 = analyzer(
    'collection_name_analyzer_v1',
    tokenizer=edge_ngram_tokenizer_v1,
    filter=['standard', 'lowercase'],
)


class CollectionV1(BaseDocType):

    document_to_protobuf_mapping = {
        'collection_name': 'name',
    }

    collection_name = String(
        analyzer=name_analyzer_v1,
        search_analyzer='default_search',
        term_vector='with_positions_offsets',
        fields={
            'raw': String(
                analyzer=raw_analyzer_v1,
                search_analyzer=raw_search,
                term_vector='with_positions_offsets',
            ),
        },
    )

    class Meta:
        doc_type = 'collection'
        all = MetaField(enabled=False)
        dynamic = MetaField('false')
        protobuf = post_containers.CollectionV1
