from elasticsearch_dsl import Q
from ...indices.actions import closed_index
from .document import ProfileV1


def create_mapping_v1(*args, **kwargs):
    with closed_index(ProfileV1._doc_type.index):
        ProfileV1.init()


def get_should_statements_v1(query):
    statements = [
        Q('match', full_name=query),
        Q('match', display_title=query),
        Q('match', email=query),
    ]
    return statements
