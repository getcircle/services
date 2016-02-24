from elasticsearch_dsl import (
    analyzer,
    MetaField,
    String,
)
from protobufs.services.team import containers_pb2 as team_containers

from ...analysis import (
    edge_ngram_tokenizer_v1,
    raw_analyzer_v1,
    raw_search,
)
from ..base import (
    BaseDocType,
    DocumentToProtobufOptions,
)


name_analyzer_v1 = analyzer(
    'team_name_analyzer_v1',
    tokenizer=edge_ngram_tokenizer_v1,
    filter=['standard', 'lowercase'],
)


class TeamV1(BaseDocType):

    document_to_protobuf_mapping = {
        'description': DocumentToProtobufOptions(
            field_name='description.value',
            on_prepare_highlight_dict=False,
        ),
        'name': DocumentToProtobufOptions(
            field_name='display_name',
            on_from_protobuf=False,
            replace=False,
        ),
    }

    name = String(
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
    description = String(
        analyzer='english',
        term_vector='with_positions_offsets',
    )

    class Meta:
        doc_type = 'team'
        all = MetaField(enabled=False)
        dynamic = MetaField('false')
        protobuf = team_containers.TeamV1
