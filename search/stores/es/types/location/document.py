from elasticsearch_dsl import (
    MetaField,
    String,
)

from protobufs.services.organization import containers_pb2 as organization_containers

from ...indices import search_v1
from ..base import BaseDocType
from . import analysis


@search_v1.INDEX.doc_type
class LocationV1(BaseDocType):
    name = String(analyzer=analysis.name_analyzer_v1)
    address_1 = String(copy_to='full_address')
    address_2 = String(copy_to='full_address')
    city = String(copy_to='full_address')
    region = String(copy_to='full_address')
    postal_code = String(copy_to='full_address')

    class Meta:
        doc_type = 'location'
        all = MetaField(enabled=False)
        dynamic = MetaField('false')
        protobuf = organization_containers.LocationV1
