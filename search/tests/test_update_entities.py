from mock import patch
from protobuf_to_dict import dict_to_protobuf
from protobufs.services.profile import containers_pb2 as profile_containers
from protobufs.services.search.containers import entity_pb2
import service.control

from services.test import (
    mocks,
    MockedTestCase,
)
from services.token import make_admin_token

from .. import tasks


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

    @patch('search.actions.update_entities.tasks.update_profile')
    def test_update_entities_profiles(self, patched):
        profiles = [mocks.mock_profile(organization_id=self.organization.id) for _ in range(2)]
        self.client.call_action(
            'update_entities',
            type=entity_pb2.PROFILE,
            ids=[p.id for p in profiles],
        )
        self.assertEqual(patched.delay.call_count, 2)
        call_args = patched.delay.call_args_list[0][0]
        self.assertEqual(call_args, (str(profiles[0].id), str(profiles[0].organization_id)))

    @patch('search.tasks.ProfileV1')
    def test_tasks_update_profile(self, patched):
        profile = mocks.mock_profile()
        self.mock.instance.register_mock_object(
            service='profile',
            action='get_profile',
            return_object=profile,
            return_object_path='profile',
            profile_id=profile.id,
            inflations={'only': ['display_title']},
        )
        tasks.update_profile(str(profile.id), str(profile.organization_id))
        self.assertEqual(patched().save.call_count, 1)
        call_args = patched.call_args_list[0][1]
        called_profile = dict_to_protobuf(call_args, profile_containers.ProfileV1, strict=False)
        self.verify_containers(profile, called_profile)
