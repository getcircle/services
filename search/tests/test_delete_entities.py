from mock import patch
from protobufs.services.search.containers import entity_pb2
import service.control

from services.test import (
    fuzzy,
    mocks,
    MockedTestCase,
)
from services.token import make_admin_token

from ..stores.es.indices.organization.actions import get_write_alias


class Test(MockedTestCase):

    def setUp(self, *args, **kwargs):
        super(Test, self).setUp(*args, **kwargs)
        self.organization = mocks.mock_organization()
        token = make_admin_token(organization_id=self.organization.id)
        self.client = service.control.Client('search', token=token)
        self.mock.instance.dont_mock_service('search')

    def test_delete_entities_ids_required(self):
        with self.assertFieldError('ids', 'MISSING'):
            self.client.call_action('delete_entities')

    @patch('search.tasks.connections')
    @patch('search.tasks.bulk')
    def test_delete_entities_profiles(self, patched, patched_connections):
        write_alias = get_write_alias(self.organization.id)
        patched_es = patched_connections.connections.get_connection()
        patched_es.indices.get_alias.return_value = {write_alias: {}}

        def _test(entity_name, entity_value):
            ids = [fuzzy.FuzzyUUID().fuzz() for _ in range(3)]
            self.client.call_action('delete_entities', type=entity_value, ids=ids)
            es_actions = patched.call_args[0][1]
            self.assertEqual(len(es_actions), len(ids))
            action = es_actions[0]
            self.assertEqual(action['_type'], entity_name)
            self.assertEqual(action['_op_type'], 'delete')
            self.assertTrue(action['_id'])
            self.assertEqual(action['_index'], write_alias)

        for key, value in entity_pb2.EntityTypeV1.items():
            _test(key.lower(), value)
