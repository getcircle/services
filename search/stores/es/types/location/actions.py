from elasticsearch_dsl import Q
from ...indices.actions import closed_index
from .document import LocationV1


def create_mapping_v1(*args, **kwargs):
    with closed_index(LocationV1._doc_type.index):
        LocationV1.init()


def get_should_statements_v1(query):
    statements = [
        Q('match', location_name=query),
        Q('match', **{'location_name.raw': {'query': query, 'boost': 3}}),
        Q('match', full_address=query),
    ]
    return statements


def get_rescore_statements_v1(query):
    statements = [
        Q('match_phrase', full_address={'query': query, 'boost': 3}),
    ]
    return statements
