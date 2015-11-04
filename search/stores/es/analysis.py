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

shingle_search = analyzer(
    'shingle_search',
    tokenizer='keyword',
    filter=['standard', 'lowercase'],
)

shingle_filter = token_filter(
    'shingle_filter',
    type='shingle',
    min_shingle_size=2,
    max_shingle_size=5,
    output_unigrams=False,
    output_unigrams_if_no_shingles=False,
)
