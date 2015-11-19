from elasticsearch_dsl import analyzer
from ...analysis import edge_ngram_max_gram_20


full_name_analyzer_v1 = analyzer(
    'profile_full_name_analyzer_v1',
    tokenizer='standard',
    filter=['standard', 'lowercase', edge_ngram_max_gram_20],
)

display_title_analyzer_v1 = analyzer(
    'profile_display_title_analyzer_v1',
    tokenizer='standard',
    filter=['standard', 'lowercase', edge_ngram_max_gram_20],
)

email_analyzer_v1 = analyzer(
    'profile_email_analyzer_v1',
    tokenizer='keyword',
    filter=['lowercase', edge_ngram_max_gram_20],
)
