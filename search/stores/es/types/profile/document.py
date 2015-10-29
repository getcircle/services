from elasticsearch_dsl import DocType, String, MetaField
from ...indices import search_v1
from . import analysis


@search_v1.INDEX.doc_type
class ProfileV1(DocType):
    full_name = String(analyzer=analysis.full_name_analyzer_v1)
    email = String()
    display_title = String(analyzer=analysis.display_title_analyzer_v1)

    class Meta:
        doc_type = 'profile'
        all = MetaField(enabled=False)
        # don't index dynamic fields
        dynamic = MetaField('false')
