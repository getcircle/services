from elasticsearch_dsl import Q

from ..base import HighlightField


def get_should_statements_v1(query):
    statements = [
        Q('match', full_name={'query': query, 'boost': 3}),
        Q('match', display_title=query),
        Q('match', **{'display_title.shingle': query}),
        #Q('match', email=query),
    ]
    return statements


def get_rescore_statements_v1(query):
    statements = [
        Q('match_phrase', full_name={'query': query, 'slop': 5}),
    ]
    return statements


def get_highlight_fields_v1(query):
    return [
        HighlightField('full_name', {}),
        HighlightField('display_title', {}),
    ]
