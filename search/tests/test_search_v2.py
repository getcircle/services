import time

from elasticsearch_dsl import connections
from protobuf_to_dict import dict_to_protobuf
from protobufs.services.post import containers_pb2 as post_containers
from protobufs.services.profile import containers_pb2 as profile_containers
from protobufs.services.search.containers import entity_pb2
from protobufs.services.search.containers import search_pb2
from protobufs.services.team import containers_pb2 as team_containers
from ..stores.es import types
import service.control
import yaml

from services.test import mocks

from .base import ESTestCase

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

    def _setup_team_fixtures(self, team_fixtures):
        if not team_fixtures:
            return

        containers = [dict_to_protobuf(f, team_containers.TeamV1) for f in team_fixtures]
        self.mock.instance.register_mock_object(
            service='team',
            action='get_teams',
            return_object=containers,
            return_object_path='teams',
            mock_regex_lookup='team:get_teams:.*',
        )
        self._update_entities(entity_pb2.TEAM, containers)

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
        es = connections.connections.get_connection()
        es.indices.delete('*')
        self.client.call_action('create_index')
        self._setup_profile_fixtures(fixtures.get('profiles', []))
        self._setup_team_fixtures(fixtures.get('teams', []))
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

    #def test_search_profile_email(self):
        #response = self.client.call_action('search_v2', query='meghan@acme.com')
        #results = response.result.results
        ## should only have 1 result since this is an exact match
        #self.assertEqual(len(results), 1)
        #top_hit = results[0]
        #profile = top_hit.profile
        #self.assertEqual(profile.email, 'meghan@acme.com')
        #self.assertEqual(profile.display_title, 'Customer Service Agent (Customer Support)')
        #self.assertEqual(profile.full_name, 'Meghan Ward')

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

    def test_search_hashtags(self):
        response = self.client.call_action('search_v2', query='#engineering')
        self.verify_top_results(
            'post',
            {'title': 'Hashtag'},
            response.result.results,
        )

    def test_search_partial_email_shouldnt_rank_higher_than_partial_name(self):
        """Several partial matches on a name should rank higher than on an email.

        Given the following two profiles:
            1:
                name: Marco Zappacosta
                email: marco@acme.com
            2:
                name: Marco de Almeida
                email: mfa@acme.com

        Searching for "Marco Almeida" should return profile 2 as the top result.
        """
        response = self.client.call_action(
            'search_v2',
            query='marco almeida',
            category=search_pb2.PROFILES,
        )
        self.verify_top_results(
            'profile',
            {'email': 'mfa@acme.com'},
            response.result.results,
            top_results=1,
        )

    #def test_search_exact_email_match(self):
        #response = self.client.call_action('search_v2', query='marco@acme.com')
        #self.verify_top_results(
            #'profile',
            #{'email': 'marco@acme.com'},
            #response.result.results,
            #top_results=1,
        #)

    def test_search_raw_content_match_higher_than_title_match(self):
        response = self.client.call_action('search_v2', query='video conferencing')
        hit = response.result.results[0]
        self.assertIn('<mark>video</mark> <mark>conferencing</mark>', hit.highlight['content'])

    def test_search_team_name_highlighting_partial(self):
        response = self.client.call_action(
            'search_v2',
            query='Dev',
            category=search_pb2.TEAMS,
        )
        hit = response.result.results[0]
        self.assertTrue(hit.highlight['name'].startswith('<mark>Dev</mark>Ops'))

    def test_search_team_name_highlighting(self):
        response = self.client.call_action(
            'search_v2',
            query='Customer Support',
            category=search_pb2.TEAMS,
        )
        hit = response.result.results[0]
        self.assertEqual(hit.highlight['name'], '<mark>Customer Support</mark>')

    def test_search_team_description_highlighting(self):
        response = self.client.call_action(
            'search_v2',
            query='site up',
            category=search_pb2.TEAMS,
        )
        hit = response.result.results[0]
        self.assertIn('<mark>site</mark> <mark>up</mark>', hit.highlight['description'])

    def test_search_profile_full_name_highlighting(self):
        response = self.client.call_action('search_v2', query='Meg')
        hit = response.result.results[0]
        self.assertTrue(hit.highlight['full_name'].startswith('<mark>Meg</mark>han'))
        response = self.client.call_action('search_v2', query='Meghan')
        hit = response.result.results[0]
        self.assertTrue(hit.highlight['full_name'].startswith('<mark>Meghan</mark>'))

        response = self.client.call_action('search_v2', query='Ward')
        hit = response.result.results[0]
        self.assertTrue(hit.highlight['full_name'].endswith('<mark>Ward</mark>'))

        response = self.client.call_action('search_v2', query='Meghan Ward')
        hit = response.result.results[0]
        self.assertEqual(hit.highlight['full_name'], '<mark>Meghan</mark> <mark>Ward</mark>')

    def test_search_profile_display_title_highlighting(self):
        response = self.client.call_action(
            'search_v2',
            query='Sr. Account',
            category=search_pb2.PROFILES,
        )
        hit = response.result.results[0]
        self.assertTrue(
            hit.highlight['display_title'].startswith(
                '<mark>Sr.</mark> <mark>Account</mark> Manager',
            )
        )

        response = self.client.call_action(
            'search_v2',
            query='Manager',
            category=search_pb2.PROFILES,
        )
        hit = response.result.results[0]
        self.assertIn('<mark>Manager</mark>', hit.highlight['display_title'])

    def test_search_post_title_highlighting(self):
        response = self.client.call_action(
            'search_v2',
            query='Arbit',
            category=search_pb2.POSTS,
        )
        hit = response.result.results[0]
        self.assertIn('<mark>Arbit</mark>er', hit.highlight['title'])

    def test_search_post_title_highlighting_return_full_fragment(self):
        response = self.client.call_action(
            'search_v2',
            query='expense',
            category=search_pb2.POSTS,
        )
        hit = response.result.results[0]
        expected_title = (
            'How do I fill out an <mark>expense</mark> report with some really really long'
            ' title to make sure that we return the full field?'
        )
        self.assertIn(expected_title, hit.highlight['title'])

    def test_search_post_content_highlighting(self):
        response = self.client.call_action(
            'search_v2',
            query='Marco Zappacosta',
            category=search_pb2.POSTS,
        )
        hit = response.result.results[0]
        self.assertIn('<mark>Marco</mark> <mark>Zappacosta</mark>', hit.highlight['content'])
        self.assertEqual(len(hit.highlight['content']), 174)

    def test_search_result_has_tracking_details(self):
        response = self.client.call_action('search_v2', query='Meghan Ward')
        hit = response.result.results[0]
        profile = hit.profile
        tracking_details = hit.tracking_details
        self.assertEqual(tracking_details.document_id, profile.id)
        self.assertEqual(tracking_details.document_type, types.ProfileV1._doc_type.name)

    def test_search_post_does_not_have_content(self):
        response = self.client.call_action(
            'search_v2',
            query='Arbiter',
            category=search_pb2.POSTS,
        )
        self.assertFalse(any([result.post.content for result in response.result.results]))

    def test_search_does_not_index_html_content(self):
        response = self.client.call_action(
            'search_v2',
            query='div strong',
            category=search_pb2.POSTS,
        )
        self.assertFalse(response.result.results)
        response = self.client.call_action(
            'search_v2',
            query='some bold section',
            category=search_pb2.POSTS,
        )
        self.assertTrue(response.result.results)
        self.assertIn(
            '<mark>Some</mark> <mark>Bold</mark> <mark>Section</mark>',
            response.result.results[0].highlight['content'],
        )
