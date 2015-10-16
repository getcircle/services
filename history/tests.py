import copy

from protobufs.services.history import containers_pb2 as history_containers
import service.control

from services.history import (
    action_container,
    action_container_for_delete,
    action_container_for_update,
)
from services.test import (
    mocks,
    TestCase,
)

from . import (
    factories,
    models,
)


class TestHistoryRecordAction(TestCase):

    def setUp(self):
        super(TestHistoryRecordAction, self).setUp()
        self.organization = mocks.mock_organization()
        self.profile = mocks.mock_profile(organization_id=self.organization.id)
        self.client = service.control.Client(
            'history',
            token=mocks.mock_token(
                organization_id=self.organization.id,
                profile_id=self.profile.id,
            ),
        )

    def test_record_action_action_required(self):
        with self.assertFieldError('action', 'MISSING'):
            self.client.call_action('record_action')

    def test_record_action_required_fields(self):
        required_fields = [
            'table_name',
            'column_name',
            'data_type',
            'action_type',
            'method_type',
        ]
        payload = {
            'table_name': 'some_table',
            'column_name': 'some_column',
            'data_type': 'varchar(64)',
            'old_value': 'old',
            'new_value': 'new',
            'action_type': history_containers.UPDATE_DESCRIPTION,
            'method_type': history_containers.UPDATE,
        }
        for field in required_fields:
            test_payload = copy.deepcopy(payload)
            test_payload.pop(field)
            with self.assertFieldError('action.%s' % (field,), 'MISSING'):
                self.client.call('record_action', action_kwargs={'action': test_payload})

    def test_record_action(self):
        expected = history_containers.ActionV1(**{
            'table_name': 'some_table',
            'column_name': 'some_column',
            'data_type': 'varchar(64)',
            'old_value': 'old',
            'new_value': 'new',
            'action_type': history_containers.UPDATE_DESCRIPTION,
            'method_type': history_containers.UPDATE,
            'primary_key_name': 'id',
            'primary_key_value': '123',
        })
        self.client.call('record_action', action_kwargs={'action': expected})
        actual = models.Action.objects.all()[0].to_protobuf()
        self.verify_containers(expected, actual)
        self.assertEqualUUID4(actual.by_profile_id, self.profile.id)
        self.assertEqualUUID4(actual.organization_id, self.organization.id)

    def test_record_action_no_old_value(self):
        self.client.call(
            'record_action',
            action_kwargs={
                'action': {
                    'table_name': 'some_table',
                    'column_name': 'some_column',
                    'data_type': 'varchar(64)',
                    'new_value': 'new',
                    'action_type': history_containers.UPDATE_DESCRIPTION,
                    'method_type': history_containers.UPDATE,
                    'primary_key_name': 'id',
                    'primary_key_value': '123',
                },
            },
        )

    def test_history_utils_action_container(self):
        action = factories.ActionFactory.create()
        container = action_container(
            action,
            'data_type',
            'new',
            history_containers.UPDATE_DESCRIPTION,
            history_containers.UPDATE,
        )
        self.assertEqual(container.column_name, 'data_type')
        self.assertEqual(container.new_value, 'new')
        self.assertEqual(container.old_value, action.data_type)
        self.assertEqual(container.action_type, history_containers.UPDATE_DESCRIPTION)
        self.assertEqual(container.method_type, history_containers.UPDATE)
        self.client.call('record_action', action_kwargs={'action': container})

    def test_history_utils_action_container_for_update(self):
        action = factories.ActionFactory.create()
        container = action_container_for_update(
            action,
            'data_type',
            'new',
            history_containers.UPDATE_DESCRIPTION,
        )
        self.assertEqual(container.column_name, 'data_type')
        self.assertEqual(container.new_value, 'new')
        self.assertEqual(container.old_value, action.data_type)
        self.assertEqual(container.action_type, history_containers.UPDATE_DESCRIPTION)
        self.assertEqual(container.method_type, history_containers.UPDATE)
        self.client.call('record_action', action_kwargs={'action': container})

    def test_history_utils_action_container_for_delete(self):
        action = factories.ActionFactory.create()
        container = action_container_for_delete(
            action,
            'data_type',
            history_containers.UPDATE_DESCRIPTION,
        )
        self.assertEqual(container.column_name, 'data_type')
        self.assertFalse(container.new_value)
        self.assertEqual(container.old_value, action.data_type)
        self.assertEqual(container.action_type, history_containers.UPDATE_DESCRIPTION)
        self.assertEqual(container.method_type, history_containers.DELETE)
        self.client.call('record_action', action_kwargs={'action': container})

    def test_history_utils_action_container_for_update_no_new_value(self):
        action = factories.ActionFactory.create()
        container = action_container_for_update(
            action,
            'data_type',
            None,
            history_containers.UPDATE_DESCRIPTION,
        )
        self.client.call('record_action', action_kwargs={'action': container})
