from elasticsearch_dsl import Q

from ..base import HighlightField


def get_should_statements_v1(query):
    statements = [
        Q('match', title=query),
        Q('match', **{'title.shingle': query}),
        Q('match', **{'title.stemmed': query}),
        Q('match', content=query),
    ]
    return statements


def get_rescore_statements_v1(query):
    statements = [
        Q('match_phrase', content={'query': query, 'boost': 2}),
    ]
    return statements


def get_highlight_fields_v1(query):
    fragment_size = 70
    return [
        HighlightField(
            'title',
            {
                'matched_fields': ['title', 'title.shingle', 'title.stemmed'],
                'number_of_fragments': 0,
            },
        ),
        HighlightField(
            'content',
            {
                'fragment_size': fragment_size,
                'no_match_size': fragment_size,
            }
        ),
    ]

def get_excluded_source_fields_v1(query):
    fields = [
        'content',
    ]
    return fields
