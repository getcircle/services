from elasticsearch_dsl import (
    MetaField,
    String,
)

from protobufs.services.organization import containers_pb2 as organization_containers

from ...analysis import (
    raw_analyzer_v1,
    raw_search,
)
from ..base import BaseDocType
from . import analysis


class LocationV1(BaseDocType):

    document_to_protobuf_mapping = {
        'location_name': 'name',
    }

    # we prefix with `location` to avoid conflicts with other documents that
    # have a `name` type.
    location_name = String(
        analyzer=analysis.name_analyzer_v1,
        fields={
            'raw': String(analyzer=raw_analyzer_v1, search_analyzer=raw_search),
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
            'raw': String(analyzer=raw_analyzer_v1, search_analyzer=raw_search),
        },
        search_analyzer='default_search',
    )

    class Meta:
        doc_type = 'location'
        all = MetaField(enabled=False)
        dynamic = MetaField('false')
        protobuf = organization_containers.LocationV1
