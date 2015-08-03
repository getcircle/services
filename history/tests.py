import copy

from protobufs.services.history import containers_pb2 as history_containers
import service.control

from services.test import (
    mocks,
    TestCase,
)

from . import (
    factories,
    models,
    utils,
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
            'column_name',
            'data_type',
            'old_value',
            'new_value',
            'action_type',
            'method_type',
        ]
        payload = {
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
                self.client.call_action('record_action', action=test_payload)

    def test_record_action(self):
        expected = history_containers.ActionV1(**{
            'column_name': 'some_column',
            'data_type': 'varchar(64)',
            'old_value': 'old',
            'new_value': 'new',
            'action_type': history_containers.UPDATE_DESCRIPTION,
            'method_type': history_containers.UPDATE,
        })
        self.client.call_action('record_action', action=expected)
        actual = models.Action.objects.all()[0].to_protobuf()
        self.verify_containers(expected, actual)
        self.assertEqualUUID4(actual.by_profile_id, self.profile.id)
        self.assertEqualUUID4(actual.organization_id, self.organization.id)

    def test_history_utils_action_container(self):
        action = factories.ActionFactory.create()
        container = utils.action_container(
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
        self.client.call_action('record_action', action=container)

    def test_history_utils_action_container_for_update(self):
        action = factories.ActionFactory.create()
        container = utils.action_container_for_update(
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
        self.client.call_action('record_action', action=container)

    def test_history_utils_action_container_for_delete(self):
        action = factories.ActionFactory.create()
        container = utils.action_container_for_delete(
            action,
            'data_type',
            history_containers.UPDATE_DESCRIPTION,
        )
        self.assertEqual(container.column_name, 'data_type')
        self.assertFalse(container.new_value)
        self.assertEqual(container.old_value, action.data_type)
        self.assertEqual(container.action_type, history_containers.UPDATE_DESCRIPTION)
        self.assertEqual(container.method_type, history_containers.DELETE)
        self.client.call_action('record_action', action=container)
