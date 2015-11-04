from elasticsearch_dsl import Q
from ...indices.actions import closed_index
from .document import TeamV1


def create_mapping_v1(*args, **kwargs):
    with closed_index(TeamV1._doc_type.index):
        TeamV1.init()


def get_should_statements_v1(query):
    statements = [
        Q('match', name=query),
        Q('match', description=query),
    ]
    return statements
