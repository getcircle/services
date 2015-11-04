from elasticsearch_dsl import Q
from ...indices.actions import closed_index
from .document import PostV1


def create_mapping_v1(*args, **kwargs):
    with closed_index(PostV1._doc_type.index):
        PostV1.init()


def get_should_statements_v1(query):
    statements = [
        Q('match', title=query),
        Q('match', **{'title.shingle': query}),
        Q('match', **{'title.stemmed': query}),
        Q('match', **{'title.raw': query}),
        Q('match', content=query),
        Q('match', **{'content.stemmed': query}),
    ]
    return statements
