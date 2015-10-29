from elasticsearch_dsl import char_filter

parens_strip = char_filter(
    'parens_strip',
    type='pattern_replace',
    pattern='[\(\)]',
    replacement='',
)
