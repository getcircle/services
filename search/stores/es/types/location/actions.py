from elasticsearch_dsl import Q

from ..base import HighlightField


def get_should_statements_v1(query):
    statements = [
        Q('match', location_name=query),
        Q('match', **{'location_name.raw': {'query': query, 'boost': 3}}),
        Q('match', full_address=query),
        Q('match', **{'full_address.shingle': {'query': query}}),
    ]
    return statements


def get_rescore_statements_v1(query):
    statements = [
        Q('match', full_address={'query': query, 'boost': 2}),
        Q('match', **{'full_address.shingle': {'query': query, 'boost': 2}}),
    ]
    return statements


def get_highlight_fields_v1(query):
    return [
        HighlightField(
            'location_name',
            {'matched_fields': ['location_name', 'location_name.raw']},
        ),
        HighlightField(
            'full_address',
            {'matched_fields': ['full_address', 'full_address.shingle']},
        ),
    ]
