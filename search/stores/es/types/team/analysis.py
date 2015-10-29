from elasticsearch_dsl import analyzer
from ...analysis import parens_strip

name_analyzer_v1 = analyzer(
    'team_name_analyzer_v1',
    tokenizer='standard',
    filter=['standard', 'lowercase', 'edgeNGram'],
    char_filter=[parens_strip],
)
