import time

from django.conf import settings
from elasticsearch_dsl import connections
from protobuf_to_dict import dict_to_protobuf
from protobufs.services.organization import containers_pb2 as organization_containers
from protobufs.services.post import containers_pb2 as post_containers
from protobufs.services.profile import containers_pb2 as profile_containers
from protobufs.services.search.containers import entity_pb2
from protobufs.services.search.containers import search_pb2
import service.control
import yaml

from services.test import mocks

from .base import ESTestCase

_fixtures = None
_executed = False


class TestSearch(ESTestCase):

    def setUp(self):
        super(TestSearch, self).setUp()
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
        super(TestSearch, cls).setUpClass()
        with open('search/fixtures/acme.yml') as read_file:
            global _fixtures
            _fixtures = yaml.load(read_file)
            cls._original = settings.SEARCH_SERVICE_SEARCH_V2_ENABLED_ORGANIZATION_IDS
            settings.SEARCH_SERVICE_SEARCH_V2_ENABLED_ORGANIZATION_IDS = [
                _fixtures['profiles'][0]['organization_id']
            ]

    @classmethod
    def tearDownClass(cls):
        settings.SEARCH_SERVICE_SEARCH_V2_ENABLED_ORGANIZATION_IDS = cls._original
        super(TestSearch, cls).tearDownClass()

    def _update_entities(self, entity_type, containers):
        es = connections.connections.get_connection()
        es.indices.delete('*')

        self.client.call_action('create_index')
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

    def verify_top_results(
            self,
            result_object_type,
            fields,
            results,
            top_results=3,
            query=None,
            should_be_present=True,
        ):
        present = False
        for result in results[:top_results]:
            result_object = getattr(result, result_object_type)
            all_match = False
            for field, expected_value in fields.iteritems():
                value = getattr(result_object, field)
                if callable(expected_value) and expected_value(value):
                    all_match = True
                elif value == expected_value:
                    all_match = True
            if all_match:
                present = True
                break

        if should_be_present:
            message = 'Expected a match in the top %s results for: %s%s' % (
                top_results,
                fields,
                ' (query: %s)' % (query,) if query else '',
            )
            self.assertTrue(present, message)
        else:
            message = 'Didn\'t expect a match in the top %s results for: %s%s' % (
                top_results,
                fields,
                ' (query: %s)' % (query,) if query else '',
            )
            self.assertFalse(present, message)

    def test_search_query_required(self):
        with self.assertFieldError('query', 'MISSING'):
            self.client.call_action('search_v2')

    def test_search_profile_email(self):
        response = self.client.call_action('search_v2', query='meghan@acme.com')
        results = response.result.results
        # should only have 1 result since this is an exact match
        self.assertEqual(len(results), 1)
        top_hit = results[0]
        profile = top_hit.profile
        self.assertEqual(profile.email, 'meghan@acme.com')
        self.assertEqual(profile.display_title, 'Customer Service Agent (Customer Support)')
        self.assertEqual(profile.full_name, 'Meghan Ward')

    def test_search_profile_partial_email(self):
        response = self.client.call_action('search_v2', query='meghan@')
        results = response.result.results
        top_hit = results[0]
        profile = top_hit.profile
        self.assertEqual(profile.email, 'meghan@acme.com')

    def test_search_profile_partial_full_name(self):
        response = self.client.call_action('search_v2', query='meg')
        self.verify_top_results(
            'profile',
            {'email': 'meghan@acme.com', 'full_name': 'Meghan Ward'},
            response.result.results,
        )

    def test_search_profile_first_name(self):
        response = self.client.call_action('search_v2', query='Meghan')
        self.verify_top_results(
            'profile',
            {'email': 'meghan@acme.com'},
            response.result.results,
        )

    def test_search_profile_last_name(self):
        response = self.client.call_action('search_v2', query='Ward')
        self.verify_top_results(
            'profile',
            {'email': 'meghan@acme.com'},
            response.result.results,
        )

    def test_search_profile_name_title(self):
        response = self.client.call_action('search_v2', query='Meg Customer Service Agent')
        self.verify_top_results(
            'profile',
            {'email': 'meghan@acme.com'},
            response.result.results,
            top_results=1,
        )

    def test_search_profile_name_department(self):
        response = self.client.call_action('search_v2', query='Meg in Customer Support')
        self.verify_top_results(
            'profile',
            {'email': 'meghan@acme.com'},
            response.result.results,
            top_results=1,
        )

    def test_search_profile_nick_name_last_name(self):
        response = self.client.call_action('search_v2', query='Meg Ward')
        self.verify_top_results(
            'profile',
            {'email': 'meghan@acme.com'},
            response.result.results,
            top_results=1,
        )

    def test_search_team_name(self):
        response = self.client.call_action('search_v2', query='Customer Support')
        self.verify_top_results(
            'team',
            {'name': 'Customer Support'},
            response.result.results,
            top_results=1,
        )

    def test_search_team_partial_name(self):
        response = self.client.call_action('search_v2', query='Customer')
        self.verify_top_results(
            'team',
            {'name': 'Customer Support'},
            response.result.results,
            top_results=1,
        )
        response = self.client.call_action('search_v2', query='Support')
        self.verify_top_results(
            'team',
            {'name': 'Customer Support'},
            response.result.results,
        )
        response = self.client.call_action('search_v2', query='Cust')
        self.verify_top_results(
            'team',
            {'name': 'Customer Support'},
            response.result.results,
        )

    def test_search_team_with_location(self):
        response = self.client.call_action('search_v2', query='Customer Support San Francisco')
        # TODO this should be the top result, "San" matches profile "Sandra"
        # because of "email", "full_name" matching "san"
        self.verify_top_results(
            'team',
            {'name': 'Customer Support'},
            response.result.results,
        )

    def test_search_location_with_name(self):
        response = self.client.call_action('search_v2', query='Headquarters')
        self.verify_top_results(
            'location',
            {'name': 'Headquarters'},
            response.result.results,
            top_results=1,
        )

    def test_search_location_address_1(self):
        response = self.client.call_action('search_v2', query='1 Front Street, Suite 2700')
        self.verify_top_results(
            'location',
            {'name': 'Headquarters'},
            response.result.results,
            top_results=1,
        )

    def test_search_location_city(self):
        response = self.client.call_action('search_v2', query='San Francisco')
        self.verify_top_results(
            'location',
            {'name': 'Headquarters'},
            response.result.results,
            top_results=1,
        )

    def test_search_location_zip_code(self):
        response = self.client.call_action('search_v2', query='94111')
        self.verify_top_results(
            'location',
            {'name': 'Headquarters'},
            response.result.results,
            top_results=1,
        )

    def test_search_location_partial_name(self):
        response = self.client.call_action('search_v2', query='Head')
        self.verify_top_results(
            'location',
            {'name': 'Headquarters'},
            response.result.results,
            top_results=1,
        )

    def test_search_location_partial_address(self):
        response = self.client.call_action('search_v2', query='1 Front')
        self.verify_top_results(
            'location',
            {'name': 'Headquarters'},
            response.result.results,
            top_results=1,
        )
        response = self.client.call_action('search_v2', query='Suite 2700')
        self.verify_top_results(
            'location',
            {'name': 'Headquarters'},
            response.result.results,
            top_results=1,
        )

    def test_search_post_phising_email(self):
        _verify = lambda response, query: self.verify_top_results(
            'post',
            {'title': lambda y: 'phishing' in y},
            response.result.results,
            top_results=1,
            query=query,
        )

        queries = [
            'phishing',
            'phishing email',
            'suspicious email',
            'suspicious call',
        ]
        for query in queries:
            response = self.client.call_action('search_v2', query=query)
            _verify(response, query)

    def test_search_post_travel_request(self):
        _verify = lambda response, query: self.verify_top_results(
            'post',
            {'title': lambda y: 'go somewhere for work' in y},
            response.result.results,
            top_results=1,
            query=query,
        )

        queries = [
            'travel request',
            'booking travel',
            'booking flight',
            'booking hotel',
            'travelling for work',
            'going to a conference',
        ]
        for query in queries:
            response = self.client.call_action('search_v2', query=query)
            _verify(response, query)

    def test_search_post_arbiter_how_to(self):
        _verify = lambda response, query: self.verify_top_results(
            'post',
            {'title': lambda y: 'What is Arbiter?'},
            response.result.results,
            query=query,
        )

        queries = [
            'Arbiter',
            'website testing framework',
        ]
        for query in queries:
            response = self.client.call_action('search_v2', query=query)
            _verify(response, query)

    def test_search_category_profiles(self):
        # verify a normal search returns a team
        response = self.client.call_action('search_v2', query='Customer Support')
        self.verify_top_results(
            'team',
            {'name': 'Customer Support'},
            response.result.results,
            top_results=1,
        )

        response = self.client.call_action(
            'search_v2',
            query='Customer Support',
            category=search_pb2.PROFILES,
        )
        self.verify_top_results(
            'profile',
            {'display_title': lambda x: 'Customer Support' in x},
            response.result.results,
            top_results=1,
        )

    def test_search_category_teams(self):
        # verify a normal search returns a person
        response = self.client.call_action('search_v2', query='Customer Support')
        self.verify_top_results(
            'profile',
            {'display_title': lambda x: 'Customer Support' in x},
            response.result.results,
            top_results=10,
        )

        response = self.client.call_action(
            'search_v2',
            query='Customer Support',
            category=search_pb2.TEAMS,
        )
        self.verify_top_results(
            'profile',
            {'display_title': lambda x: 'Customer Support' in x},
            response.result.results,
            top_results=10,
            should_be_present=False,
        )

    def test_search_category_locations(self):
        # verify a normal search returns a person
        response = self.client.call_action('search_v2', query='San Francisco')
        self.verify_top_results(
            'profile',
            {'full_name': lambda x: 'Sandra' in x},
            response.result.results,
        )

        response = self.client.call_action(
            'search_v2',
            query='San Francisco',
            category=search_pb2.LOCATIONS,
        )
        self.verify_top_results(
            'profile',
            {'full_name': lambda x: 'Sandra' in x},
            response.result.results,
            top_results=10,
            should_be_present=False,
        )

    def test_search_category_posts(self):
        # verify a normal search returns a person
        response = self.client.call_action('search_v2', query='Taylor')
        self.verify_top_results(
            'profile',
            {'full_name': lambda x: 'Taylor' in x},
            response.result.results,
        )

        response = self.client.call_action(
            'search_v2',
            query='Taylor',
            category=search_pb2.POSTS,
        )
        self.verify_top_results(
            'profile',
            {'full_name': lambda x: 'Taylor' in x},
            response.result.results,
            top_results=10,
            should_be_present=False,
        )

    def test_search_v2_feature_flag(self):
        with self.settings(
            SEARCH_SERVICE_SEARCH_V2_ENABLED_ORGANIZATION_IDS=[],
            SEARCH_V2_ENABLED=False,
        ):
            response = self.client.call_action('search_v2', query='Taylor')
            self.assertFalse(len(response.result.results))
        response = self.client.call_action('search_v2', query='Taylor')
        self.assertTrue(len(response.result.results))

    def test_search_hashtags(self):
        response = self.client.call_action('search_v2', query='#engineering')
        self.verify_top_results(
            'post',
            {'title': 'Hashtag'},
            response.result.results,
        )
