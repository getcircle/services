from elasticsearch_dsl import (
    analyzer,
    MetaField,
    String,
)

from protobufs.services.organization import containers_pb2 as organization_containers

from ...analysis import (
    edge_ngram_tokenizer_v1,
    raw_analyzer_v1,
    raw_search,
    shingle_filter,
    shingle_search,
)
from ..base import BaseDocType

# support autocomplete for location names
name_analyzer_v1 = analyzer(
    'location_name_analyzer_v1',
    tokenizer=edge_ngram_tokenizer_v1,
    filter=['standard', 'lowercase'],
)

full_address_shingle_analyzer_v1 = analyzer(
    'full_address_shingle_analyzer_v1',
    tokenizer='standard',
    filter=['standard', 'lowercase', shingle_filter],
)


class LocationV1(BaseDocType):

    document_to_protobuf_mapping = {
        'location_name': 'name',
    }

    # we prefix with `location` to avoid conflicts with other documents that
    # have a `name` type.
    location_name = String(
        analyzer=name_analyzer_v1,
        fields={
            'raw': String(analyzer=raw_analyzer_v1, search_analyzer=raw_search),
        },
        search_analyzer='default_search',
        term_vector='with_positions_offsets',
    )
    address_1 = String(copy_to='full_address')
    address_2 = String(copy_to='full_address')
    city = String(copy_to='full_address')
    region = String(copy_to='full_address')
    postal_code = String(copy_to='full_address')
    full_address = String(
        analyzer=name_analyzer_v1,
        search_analyzer='default_search',
        fields={
            'shingle': String(
                analyzer=full_address_shingle_analyzer_v1,
                search_analyzer=shingle_search,
            ),
        },
        term_vector='with_positions_offsets',
        store=True,
    )

    class Meta:
        doc_type = 'location'
        all = MetaField(enabled=False)
        dynamic = MetaField('false')
        protobuf = organization_containers.LocationV1
