from elasticsearch_dsl import Q

from ..base import HighlightField


def get_should_statements_v1(query):
    statements = [
        Q('match', collection_name={'query': query, 'boost': 2}),
        Q('match', **{'collection_name.raw': {'query': query, 'boost': 3}}),
    ]
    return statements


def get_highlight_fields_v1(query):
    return [
        HighlightField(
            'collection_name',
            {'matched_fields': ['collection_name', 'collection_name.raw']},
        ),
    ]
