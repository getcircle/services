from elasticsearch_dsl import DocType, String, MetaField
from ...indices import search_v1
from . import analysis


@search_v1.INDEX.doc_type
class TeamV1(DocType):
    name = String(analyzer=analysis.name_analyzer_v1)
    description = String(analyzer='english')

    class Meta:
        doc_type = 'team'
        all = MetaField(enabled=False)
        dynamic = MetaField('false')
