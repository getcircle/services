from elasticsearch_dsl import (
    MetaField,
    String,
)

from protobufs.services.organization import containers_pb2 as organization_containers

from ...analysis import shingle_search
from ...indices import search_v1
from ..base import BaseDocType
from . import analysis


@search_v1.INDEX.doc_type
class LocationV1(BaseDocType):

    document_to_protobuf_mapping = {
        'location_name': 'name',
    }

    location_name = String(
        analyzer=analysis.name_analyzer_v1,
        fields={
            'shingle': String(
                analyzer=analysis.name_shingle_analyzer_v1,
                search_analyzer=shingle_search,
            ),
        },
        search_analyzer='default_search',
    )
    address_1 = String(copy_to='full_address')
    address_2 = String(copy_to='full_address')
    city = String(copy_to='full_address')
    region = String(copy_to='full_address')
    postal_code = String(copy_to='full_address')
    organization_id = String(index='not_analyzed')
    full_address = String(
        analyzer=analysis.name_analyzer_v1,
        fields={
            'shingle': String(
                analyzer=analysis.name_shingle_analyzer_v1,
                search_analyzer=shingle_search,
            ),
        },
        search_analyzer='default_search',
    )

    class Meta:
        doc_type = 'location'
        all = MetaField(enabled=False)
        dynamic = MetaField('false')
        protobuf = organization_containers.LocationV1
