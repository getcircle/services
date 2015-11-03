from protobuf_to_dict import dict_to_protobuf
from protobufs.services.organization import containers_pb2 as organization_containers
from protobufs.services.post import containers_pb2 as post_containers
from protobufs.services.profile import containers_pb2 as profile_containers
from protobufs.services.search.containers import entity_pb2
import service.control
import yaml

from services.test import mocks

from .base import ESTestCase

_fixtures = None


class TestSearch(ESTestCase):

    def setUp(self):
        super(TestSearch, self).setUp()
        organization_id = _fixtures['profiles'][0]['organization_id']
        self.organization = mocks.mock_organization(id=organization_id)
        self.profile = mocks.mock_profile(organization_id=self.organization.id)
        token = mocks.mock_token(profile_id=self.profile.id, organization_id=self.organization.id)
        self.client = service.control.Client('search', token=token)
        self.mock.instance.dont_mock_service('search')
        self._setup_fixtures(_fixtures)

    @classmethod
    def setUpClass(cls):
        super(TestSearch, cls).setUpClass()
        with open('search/fixtures/acme.yml') as read_file:
            global _fixtures
            _fixtures = yaml.load(read_file)

    def _update_entities(self, entity_type, containers):
        self.client.call_action(
            'update_entities',
            type=entity_type,
            ids=[c.id for c in containers],
        )

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

    def _setup_team_fixtures(self, team_fixtures):
        if not team_fixtures:
            return

        containers = [dict_to_protobuf(f, organization_containers.TeamV1) for f in team_fixtures]
        self.mock.instance.register_mock_object(
            service='organization',
            action='get_teams',
            return_object=containers,
            return_object_path='teams',
            mock_regex_lookup='organization:get_teams:.*',
        )
        self._update_entities(entity_pb2.TEAM, containers)

    def _setup_location_fixtures(self, location_fixtures):
        if not location_fixtures:
            return

        containers = [dict_to_protobuf(f, organization_containers.LocationV1) for f
                      in location_fixtures]
        self.mock.instance.register_mock_object(
            service='organization',
            action='get_locations',
            return_object=containers,
            return_object_path='locations',
            mock_regex_lookup='organization:get_locations:.*',
        )
        self._update_entities(entity_pb2.LOCATION, containers)

    def _setup_post_fixtures(self, post_fixtures):
        if not post_fixtures:
            return

        containers = [dict_to_protobuf(f, post_containers.PostV1) for f in post_fixtures]
        self.mock.instance.register_mock_object(
            service='post',
            action='get_posts',
            return_object=containers,
            return_object_path='posts',
            mock_regex_lookup='post:get_posts:.*',
        )
        self._update_entities(entity_pb2.POST, containers)

    def _setup_fixtures(self, fixtures):
        self._setup_profile_fixtures(fixtures.get('profiles', []))
        self._setup_team_fixtures(fixtures.get('teams', []))
        self._setup_location_fixtures(fixtures.get('locations', []))
        self._setup_post_fixtures(fixtures.get('posts', []))

    def test_search_query_required(self):
        with self.assertFieldError('query', 'MISSING'):
            self.client.call_action('search_v2')

    def test_search_profile_full_name(self):
        response = self.client.call_action('search_v2', query='meghan@acme.com')
        results = response.result.results
        self.assertEqual(len(results), 1)
