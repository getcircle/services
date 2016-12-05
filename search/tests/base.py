from django.conf import settings
from elasticsearch.helpers import (
    bulk,
    scan,
)
from elasticsearch_dsl import connections
from services.test import MockedTestCase


def _delete_all_documents():
    """Delete all documents within the test ES instance"""
    # NB: This relies on tests using a separate ES instance and will delete all
    # documents. This should never be called on production. This is a naive
    # check to ensure that we're not in produciton.
    if not settings.TESTS_TEARDOWN_ES:
        raise ValueError('TESTS_TEARDOWN_ES is not True, refusing to delete documents')

    es = connections.connections.get_connection()
    bulk_requests = []
    for d in scan(es):
        d['_op_type'] = 'delete'
        bulk_requests.append(d)
    bulk(es, bulk_requests, raise_on_error=False)


class ESTestCase(MockedTestCase):

    @classmethod
    def setUpClass(cls):
        super(ESTestCase, cls).setUpClass()
        _delete_all_documents()
