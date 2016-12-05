from elasticsearch_dsl import Q

from ..base import HighlightField


def get_should_statements_v1(query):
    statements = [
        Q('match', name={'query': query, 'boost': 2}),
        Q('match', **{'name.raw': {'query': query, 'boost': 3}}),
        Q('match', description=query),
    ]
    return statements


def get_highlight_fields_v1(query):
    return [
        HighlightField('name', {'matched_fields': ['name', 'name.raw']}),
        HighlightField('description', {}),
    ]
