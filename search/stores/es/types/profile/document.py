from elasticsearch_dsl import (
    analyzer,
    MetaField,
    String,
)
from protobufs.services.profile import containers_pb2 as profile_containers

from ..base import BaseDocType
from ...analysis import (
    edge_ngram_tokenizer_v1,
    raw_search,
)

full_name_analyzer_v1 = analyzer(
    'profile_full_name_analyzer_v1',
    tokenizer=edge_ngram_tokenizer_v1,
    filter=['standard', 'lowercase'],
)

display_title_analyzer_v1 = analyzer(
    'profile_display_title_analyzer_v1',
    tokenizer=edge_ngram_tokenizer_v1,
    filter=['standard', 'lowercase'],
)

email_analyzer_v1 = analyzer(
    'profile_email_analyzer_v1',
    tokenizer='uax_url_email',
    filter=['lowercase'],
)


class ProfileV1(BaseDocType):
    full_name = String(
        analyzer=full_name_analyzer_v1,
        search_analyzer='default_search',
        term_vector='with_positions_offsets',
    )
    email = String(analyzer=email_analyzer_v1, search_analyzer=raw_search)
    display_title = String(
        analyzer=display_title_analyzer_v1,
        search_analyzer='default_search',
    )

    class Meta:
        doc_type = 'profile'
        all = MetaField(enabled=False)
        # don't index dynamic fields
        dynamic = MetaField('false')
        protobuf = profile_containers.ProfileV1
