from elasticsearch_dsl import Q


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
