import service.control

from services.test import (
    fuzzy,
    mocks,
    MockedTestCase,
)

from ..factories import UserFactory
from ..models import User


class Test(MockedTestCase):

    def setUp(self):
        super(Test, self).setUp()
        self.organization_id = fuzzy.uuid()
        self.mock.instance.dont_mock_service('user')
        token = mocks.mock_token(organization_id=self.organization_id)
        self.client = service.control.Client('user', token=token)

    def test_bulk_update_users(self):
        users = UserFactory.create_batch(size=2, organization_id=self.organization_id)
        self.client.call_action(
            'bulk_update_users',
            users=[user.to_protobuf(is_active=False) for user in users],
        )

        users = User.objects.filter(organization_id=self.organization_id)
        self.assertFalse(any([u.is_active for u in users]))

    def test_bulk_update_users_users_required(self):
        with self.assertFieldError('users', 'MISSING'):
            self.client.call_action('bulk_update_users')

    def test_bulk_update_users_organization_id_and_id_cant_change(self):
        user = UserFactory.create(organization_id=self.organization_id)
        self.client.call_action(
            'bulk_update_users',
            users=[user.to_protobuf(organization_id=fuzzy.uuid())],
        )
        User.objects.get(organization_id=user.organization_id, id=user.id)

        self.client.call_action(
            'bulk_update_users',
            users=[user.to_protobuf(id=fuzzy.uuid(), organization_id=fuzzy.uuid())],
        )
        User.objects.get(organization_id=user.organization_id, id=user.id)
