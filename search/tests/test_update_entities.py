from mock import patch
from protobuf_to_dict import dict_to_protobuf
from protobufs.services.organization import containers_pb2 as organization_containers
from protobufs.services.post import containers_pb2 as post_containers
from protobufs.services.profile import containers_pb2 as profile_containers
from protobufs.services.search.containers import entity_pb2
import service.control

from services.test import (
    mocks,
    MockedTestCase,
)
from services.token import make_admin_token

from .. import tasks
from ..actions.update_entities import get_batches
from ..stores.es import types
from ..stores.es.indices.organization.actions import get_write_alias


class TestUpdateEntities(MockedTestCase):

    def setUp(self):
        super(TestUpdateEntities, self).setUp()
        self.organization = mocks.mock_organization()
        token = make_admin_token(organization_id=self.organization.id)
        self.client = service.control.Client('search', token=token)
        self.mock.instance.dont_mock_service('search')

        self.patcher = patch('search.tasks.connections')
        patched_connections = self.patcher.start()
        connection = patched_connections.connections.get_connection()
        connection.indices.get_alias.return_value = {get_write_alias(self.organization.id): {}}

    def tearDown(self):
        super(TestUpdateEntities, self).tearDown()
        self.patcher.stop()

    def test_update_entities_ids_required(self):
        with self.assertFieldError('ids', 'MISSING'):
            self.client.call_action('update_entities')

    @patch('search.actions.update_entities.tasks.update_profiles')
    def test_update_entities_profiles(self, patched):
        profiles = [mocks.mock_profile(organization_id=self.organization.id) for _ in range(2)]
        self.client.call_action(
            'update_entities',
            type=entity_pb2.PROFILE,
            ids=[p.id for p in profiles],
        )
        self.assertEqual(patched.delay.call_count, 1)
        call_args = patched.delay.call_args_list[0][0]
        self.assertEqual(
            call_args,
            ([str(p.id) for p in profiles], str(profiles[0].organization_id))
        )

    @patch('search.tasks.bulk')
    def test_tasks_update_profiles(self, patched_bulk):
        profile = mocks.mock_profile()
        self.mock.instance.register_mock_object(
            service='profile',
            action='get_profiles',
            return_object=[profile],
            return_object_path='profiles',
            ids=[profile.id],
            inflations={'disabled': False, 'only': ['display_title']},
            is_admin=False,
        )
        tasks.update_profiles([str(profile.id)], str(profile.organization_id))
        self.assertEqual(patched_bulk.call_count, 1)

        documents = patched_bulk.call_args_list[0][0][1]
        called_profile = dict_to_protobuf(
            documents[0]['_source'],
            profile_containers.ProfileV1,
            strict=False,
        )
        self.verify_containers(profile, called_profile)

    def test_get_batches(self):
        # test batch with no remainder
        batches = get_batches(range(30), batch_size=10)
        self.assertEqual(len(batches), 3)
        [self.assertEqual(len(batch), 10) for batch in batches]

        # test batch with remainder
        batches = get_batches(range(33), batch_size=10)
        self.assertEqual(len(batches), 4)
        [self.assertEqual(len(batch), 10) for batch in batches[:-1]]
        self.assertEqual(len(batches[-1]), 3)

    @patch('search.actions.update_entities.tasks.update_teams')
    def test_update_entities_teams(self, patched):
        teams = [mocks.mock_team(organization_id=self.organization.id) for _ in range(2)]
        self.client.call_action(
            'update_entities',
            type=entity_pb2.TEAM,
            ids=[t.id for t in teams],
        )
        self.assertEqual(patched.delay.call_count, 1)
        call_args = patched.delay.call_args_list[0][0]
        self.assertEqual(
            call_args,
            ([str(t.id) for t in teams], str(teams[0].organization_id))
        )

    @patch('search.tasks.bulk')
    def test_tasks_update_teams(self, patched_bulk):
        team = mocks.mock_team()
        self.mock.instance.register_mock_object(
            service='organization',
            action='get_teams',
            return_object=[team],
            return_object_path='teams',
            ids=[team.id],
        )
        tasks.update_teams([str(team.id)], str(team.organization_id))
        self.assertEqual(patched_bulk.call_count, 2)

        documents = patched_bulk.call_args_list[0][0][1]
        called_team = dict_to_protobuf(
            documents[0]['_source'],
            organization_containers.TeamV1,
            strict=False,
        )
        self.verify_containers(team, called_team)

    @patch('search.actions.update_entities.tasks.update_locations')
    def test_update_entities_locations(self, patched):
        locations = [mocks.mock_location(organization_id=self.organization.id) for _ in range(2)]
        self.client.call_action(
            'update_entities',
            type=entity_pb2.LOCATION,
            ids=[l.id for l in locations],
        )
        self.assertEqual(patched.delay.call_count, 1)
        call_args = patched.delay.call_args_list[0][0]
        self.assertEqual(
            call_args,
            ([str(l.id) for l in locations], str(locations[0].organization_id))
        )

    @patch('search.tasks.bulk')
    def test_tasks_update_locations(self, patched_bulk):
        location = mocks.mock_location()
        self.mock.instance.register_mock_object(
            service='organization',
            action='get_locations',
            return_object=[location],
            return_object_path='locations',
            ids=[location.id],
        )
        tasks.update_locations([str(location.id)], str(location.organization_id))
        self.assertEqual(patched_bulk.call_count, 1)

        documents = patched_bulk.call_args_list[0][0][1]
        types.LocationV1.prepare_protobuf_dict(documents[0]['_source'])
        called_location = dict_to_protobuf(
            documents[0]['_source'],
            organization_containers.LocationV1,
            strict=False,
        )
        self.verify_containers(location, called_location)

    @patch('search.actions.update_entities.tasks.update_posts')
    def test_update_entities_posts(self, patched):
        posts = [mocks.mock_post(organization_id=self.organization.id) for _ in range(2)]
        self.client.call_action(
            'update_entities',
            type=entity_pb2.POST,
            ids=[p.id for p in posts],
        )
        self.assertEqual(patched.delay.call_count, 1)
        call_args = patched.delay.call_args_list[0][0]
        self.assertEqual(
            call_args,
            ([str(p.id) for p in posts], str(posts[0].organization_id))
        )

    @patch('search.tasks.bulk')
    def test_tasks_update_posts(self, patched_bulk):
        post = mocks.mock_post(created=None, changed=None)
        self.mock.instance.register_mock_object(
            service='post',
            action='get_posts',
            return_object=[post],
            return_object_path='posts',
            ids=[post.id],
            state=post_containers.LISTED,
            inflations={'disabled': False, 'only': ['by_profile']},
            all_states=False,
        )
        tasks.update_posts([str(post.id)], str(post.organization_id))
        self.assertEqual(patched_bulk.call_count, 1)

        documents = patched_bulk.call_args_list[0][0][1]
        called_post = dict_to_protobuf(
            documents[0]['_source'],
            post_containers.PostV1,
            strict=False,
        )
        self.verify_containers(post, called_post)

    @patch('search.tasks.bulk')
    def test_tasks_update_direct_reports(self, patched_bulk):
        manager = mocks.mock_profile()
        direct_report = mocks.mock_profile(organization_id=manager.organization_id)
        self.mock.instance.register_mock_object(
            service='organization',
            action='get_profile_reporting_details',
            return_object=[direct_report.id],
            return_object_path='direct_reports_profile_ids',
            profile_id=manager.id,
        )
        self.mock.instance.register_mock_object(
            service='profile',
            action='get_profiles',
            return_object=[direct_report],
            return_object_path='profiles',
            ids=[direct_report.id],
            inflations={'disabled': False, 'only': ['display_title']},
            is_admin=False,
        )

        tasks.update_direct_reports(str(manager.id), str(manager.organization_id))
        self.assertEqual(patched_bulk.call_count, 1)

        documents = patched_bulk.call_args_list[0][0][1]
        called_profile = dict_to_protobuf(
            documents[0]['_source'],
            profile_containers.ProfileV1,
            strict=False,
        )
        self.verify_containers(direct_report, called_profile)
