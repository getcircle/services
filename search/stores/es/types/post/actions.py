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
    return [
        HighlightField(
            'title',
            {
                'matched_fields': ['title', 'title.shingle', 'title.stemmed'],
                'number_of_fragments': 0,
            },
        ),
        HighlightField('content', {'fragment_size': 70, 'no_match_size': 70}),
    ]
