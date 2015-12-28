import time
from elasticsearch_dsl import connections
from services.test import (
    fuzzy,
    MockedTestCase,
)

from ..actions.migrations import (
    get_indices_to_migrate,
    migrate_index,
)
from ..tasks import (
    _bulk_actions,
    _get_write_indices_for_organization_id,
)
from ..stores.es import types
from ..stores.es.indices.organization.actions import (
    create_index,
    get_read_alias,
    get_write_alias,
)


class Test(MockedTestCase):

    def setUp(self, *args, **kwargs):
        super(Test, self).setUp(*args, **kwargs)
        self.es = connections.connections.get_connection()

    def tearDown(self, *args, **kwargs):
        super(Test, self).tearDown(*args, **kwargs)
        self.es.indices.delete('*')

    def test_get_indices_to_migrate(self):
        # create some indices that don't match the current version
        create_index(fuzzy.FuzzyUUID().fuzz(), version=1)
        create_index(fuzzy.FuzzyUUID().fuzz(), version=2)
        create_index(fuzzy.FuzzyUUID().fuzz(), version=3)
        # create indices that match the current version
        create_index(fuzzy.FuzzyUUID().fuzz(), version=4)

        indices_to_migrate = get_indices_to_migrate(current_version=4)
        self.assertEqual(len(indices_to_migrate), 3)
        for index in indices_to_migrate:
            self.assertFalse(index.endswith('_v4'))

    def test_create_index_contains_new_mappings(self):
        index = create_index(fuzzy.FuzzyUUID().fuzz())
        mappings = index._get_mappings()[0]
        self.assertEqual(len(mappings.keys()), 4)

    def test_migrate_new_index_write_to_both_while_migrating(self):
        organization_id = fuzzy.FuzzyUUID().fuzz()
        organization_id_2 = fuzzy.FuzzyUUID().fuzz()
        # create indices for another organization to ensure we're not indexing
        # in both orgs
        create_index(organization_id_2, version=1)
        create_index(organization_id_2, version=2, check_duplicate=False)

        old_index = create_index(organization_id, version=1)
        new_index = create_index(organization_id, version=2, check_duplicate=False)
        # verify we write to both indices when updating documents
        profile = types.ProfileV1(full_name='Saved in both indices')

        write_indices = _get_write_indices_for_organization_id(self.es, organization_id)
        self.assertEqual(len(write_indices), 2)
        for index in write_indices:
            self.assertTrue(index.startswith(organization_id))

        _bulk_actions([profile.to_dict(include_meta=True)], organization_id)
        time.sleep(2)
        self.assertEqual(len(old_index.search().execute().hits), 1)
        self.assertEqual(len(new_index.search().execute().hits), 1)

        # verify the read alias is still the old index
        read_aliases = self.es.indices.get_alias('*', get_read_alias(organization_id))
        self.assertEqual(len(read_aliases.keys()), 1)
        self.assertEqual(read_aliases.keys()[0], old_index._name)
        write_aliases = self.es.indices.get_alias('*', get_write_alias(organization_id))
        self.assertEqual(len(write_aliases.keys()), 2)

    def test_migrate_index(self):
        organization_id = fuzzy.FuzzyUUID().fuzz()
        old_index = create_index(organization_id, version=1)
        write_alias = get_write_alias(organization_id)
        # create one of each object in the old index
        types.ProfileV1(_index=write_alias, full_name='Test').save()
        types.LocationV1(_index=write_alias, name='Headquarters').save()
        types.TeamV1(_index=write_alias, name='Founders').save()
        types.PostV1(_index=write_alias, title='Some Post').save()
        time.sleep(2)
        self.assertEqual(len(old_index.search().execute().hits), 4)
        new_index = migrate_index(old_index._name, current_version=2)
        time.sleep(2)
        self.assertEqual(len(new_index.search().execute().hits), 4)

        # verify we've transitioned the aliases over to the new index
        read_aliases = self.es.indices.get_alias('*', get_read_alias(organization_id))
        self.assertEqual(len(read_aliases.keys()), 1)
        self.assertEqual(read_aliases.keys()[0], new_index._name)
        write_aliases = self.es.indices.get_alias('*', get_write_alias(organization_id))
        self.assertEqual(len(write_aliases.keys()), 1)
        self.assertEqual(write_aliases.keys()[0], new_index._name)
        self.assertFalse(self.es.indices.exists(old_index._name))
