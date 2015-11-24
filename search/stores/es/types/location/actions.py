from elasticsearch_dsl import Q


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
