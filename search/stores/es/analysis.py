from elasticsearch_dsl import (
    analyzer,
    token_filter,
    tokenizer,
)

edge_ngram_tokenizer_v1 = tokenizer(
    'edge_ngram_v1',
    type='edgeNGram',
    min_gram=1,
    max_gram=20,
    token_chars=['letter', 'digit', 'punctuation'],
)

default_search = analyzer(
    'default_search',
    tokenizer='whitespace',
    filter=['standard', 'lowercase'],
)

raw_search = analyzer(
    'raw_search',
    tokenizer='keyword',
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

raw_analyzer_v1 = analyzer(
    'raw_analyzer_v1',
    tokenizer='keyword',
    filter=['standard', 'lowercase'],
)
