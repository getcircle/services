from elasticsearch_dsl import connections
import service.control

from services.test import (
    mocks,
    MockedTestCase,
)

from ..stores.es.indices.organization import INDEX_VERSION
from ..stores.es.indices.organization.actions import (
    get_index_name,
    get_read_alias,
    get_write_alias,
)


class Test(MockedTestCase):

    def setUp(self, *args, **kwargs):
        super(Test, self).setUp(*args, **kwargs)
        self.organization = mocks.mock_organization()
        self.token = mocks.mock_token(organization_id=self.organization.id)
        self.client = service.control.Client('search', token=self.token)
        self.mock.instance.dont_mock_service('search')

    def tearDown(self, *args, **kwargs):
        super(Test, self).tearDown(*args, **kwargs)
        es = connections.connections.get_connection()
        es.indices.delete('*')

    def test_stores_es_indices_organization_get_index_name(self):
        index_name = get_index_name(self.organization.id)
        self.assertEqual(index_name, '%s_v%s' % (self.organization.id, INDEX_VERSION))

    def test_search_create_index(self):
        self.client.call_action('create_index')
        es = connections.connections.get_connection()
        read_alias = get_read_alias(self.organization.id)
        write_alias = get_write_alias(self.organization.id)
        self.assertTrue(es.indices.exists_alias('*', read_alias))
        self.assertTrue(es.indices.exists_alias('*', write_alias))

    def test_search_create_index_duplicate_error(self):
        self.client.call_action('create_index')
        with self.assertFieldError('token.organization_id', 'DUPLICATE'):
            self.client.call_action('create_index')
