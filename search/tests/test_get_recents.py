import time
import service.control
import yaml

from services.test import mocks
from .base import ESTestCase
from elasticsearch_dsl import connections
from protobuf_to_dict import dict_to_protobuf
from protobufs.services.organization import containers_pb2 as organization_containers
from protobufs.services.post import containers_pb2 as post_containers
from protobufs.services.profile import containers_pb2 as profile_containers
from protobufs.services.search.containers import entity_pb2
from protobufs.services.search.containers import search_pb2
from ..stores.es import types
from .. import (
    factories,
    models
)


_fixtures = None
_executed = False


class Test(ESTestCase):

    def setUp(self):
        super(Test, self).setUp()
        organization_id = _fixtures['profiles'][0]['organization_id']
        self.organization = mocks.mock_organization(id=organization_id)
        self.profile = mocks.mock_profile(organization_id=self.organization.id)
        token = mocks.mock_token(profile_id=self.profile.id, organization_id=self.organization.id)
        self.client = service.control.Client('search', token=token)
        self.mock.instance.dont_mock_service('search')
        global _executed
        if not _executed:
            self._setup_fixtures(_fixtures)
            _executed = True

    @classmethod
    def setUpClass(cls):
        super(Test, cls).setUpClass()
        with open('search/fixtures/acme.yml') as read_file:
            global _fixtures
            _fixtures = yaml.load(read_file)

    def _update_entities(self, entity_type, containers):
        self.client.call_action(
            'update_entities',
            type=entity_type,
            ids=[c.id for c in containers],
        )
        # give the documents time to index
        time.sleep(1)

    def _setup_profile_fixtures(self, profile_fixtures):
        if not profile_fixtures:
            return

        containers = [dict_to_protobuf(f, profile_containers.ProfileV1) for f in profile_fixtures]
        self.mock.instance.register_mock_object(
            service='profile',
            action='get_profiles',
            return_object=containers,
            return_object_path='profiles',
            mock_regex_lookup='profile:get_profiles:.*',
        )
        self._update_entities(entity_pb2.PROFILE, containers)

    def _setup_fixtures(self, fixtures):
        es = connections.connections.get_connection()
        es.indices.delete('*')
        self.client.call_action('create_index')
        self._setup_profile_fixtures(fixtures.get('profiles', []))

    def test_get_recents_current_user(self):
        document_type = 'profile'
        document_id = _fixtures['profiles'][0]['id']

        # User's recents
        factories.RecentFactory.create_batch(size=2, profile=self.profile, document_type=document_type, document_id=document_id)
        # Others' recents
        factories.RecentFactory.create_batch(size=2, document_type=document_type, document_id=document_id)

        response = self.client.call_action('get_recents')
        self.assertEqual(len(response.result.recents), 2)
