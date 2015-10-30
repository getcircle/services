from mock import patch
from protobufs.services.search.containers import entity_pb2
import service.control

from services.test import (
    mocks,
    MockedTestCase,
)
from services.token import make_admin_token

from .. import tasks
from ..actions.update_entities import get_batches


class TestUpdateEntities(MockedTestCase):

    def setUp(self):
        super(TestUpdateEntities, self).setUp()
        self.organization = mocks.mock_organization()
        token = make_admin_token(organization_id=self.organization.id)
        self.client = service.control.Client('search', token=token)
        self.mock.instance.dont_mock_service('search')

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
    @patch('search.tasks.connections')
    def test_tasks_update_profiles(self, patched_connection, patched_bulk):
        profile = mocks.mock_profile()
        self.mock.instance.register_mock_object(
            service='profile',
            action='get_profiles',
            return_object=[profile],
            return_object_path='profiles',
            ids=[profile.id],
            inflations={'only': ['display_title']},
        )
        tasks.update_profiles([str(profile.id)], str(profile.organization_id))
        self.assertEqual(patched_bulk.call_count, 1)

        documents = patched_bulk.call_args_list[0][0][1]
        called_profile = documents[0].to_protobuf()
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
