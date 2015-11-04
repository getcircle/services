from elasticsearch_dsl import Q
from ...indices.actions import closed_index
from .document import LocationV1


def create_mapping_v1(*args, **kwargs):
    with closed_index(LocationV1._doc_type.index):
        LocationV1.init()


def get_should_statements_v1(query):
    statements = [
        Q('match', location_name=query),
        Q('match', **{'location_name.shingle': query}),
        Q('match', full_address=query),
        Q('match', **{'full_address.shingle': query}),
    ]
    return statements
