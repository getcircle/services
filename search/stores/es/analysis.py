from elasticsearch_dsl import (
    analyzer,
    char_filter,
    token_filter,
)

parens_strip = char_filter(
    'parens_strip',
    type='pattern_replace',
    pattern='[\(\)]',
    replacement='',
)

edge_ngram_max_gram_20 = token_filter(
    'edge_ngram_max_gram_20',
    type='edgeNGram',
    min_gram=1,
    max_gram=20,
)

default_search = analyzer(
    'default_search',
    tokenizer='whitespace',
    filter=['standard', 'lowercase'],
)
