from elasticsearch_dsl import analyzer
from ...analysis import parens_strip

full_name_analyzer_v1 = analyzer(
    'profile_full_name_analyzer_v1',
    tokenizer='standard',
    filter=['standard', 'lowercase', 'edgeNGram'],
    char_filter=[parens_strip],
)

display_title_analyzer_v1 = analyzer(
    'profile_display_title_analyzer_v1',
    tokenizer='standard',
    filter=['standard', 'lowercase', 'edgeNGram'],
    char_filter=[parens_strip],
)
