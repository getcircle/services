from elasticsearch_dsl import analyzer
from ...analysis import (
    edge_ngram_max_gram_20,
    shingle_filter,
)

name_analyzer_v1 = analyzer(
    'location_name_analyzer_v1',
    tokenizer='standard',
    filter=['standard', 'lowercase', edge_ngram_max_gram_20],
)

name_shingle_analyzer_v1 = analyzer(
    'location_name_shingle_analyzer_v1',
    tokenizer='standard',
    filter=['standard', 'lowercase', shingle_filter],
)
