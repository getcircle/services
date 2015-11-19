from elasticsearch_dsl import analyzer
from ...analysis import edge_ngram_max_gram_20

# support autocomplete for location names
name_analyzer_v1 = analyzer(
    'location_name_analyzer_v1',
    tokenizer='standard',
    filter=['standard', 'lowercase', edge_ngram_max_gram_20],
)
