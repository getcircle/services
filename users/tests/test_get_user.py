import service.control
from services.test import (
    mocks,
    MockedTestCase,
)

from .. import factories


class GetUserTests(MockedTestCase):

    def setUp(self):
        super(GetUserTests, self).setUp()
        self.requester = factories.UserFactory.create()
        token = mocks.mock_token(
            user_id=str(self.requester.id),
            organization_id=str(self.requester.organization_id),
        )
        self.client = service.control.Client('user', token=token)
        self.mock.instance.dont_mock_service('user')

    def test_get_user_email(self):
        user = factories.UserFactory.create(organization_id=self.requester.organization_id)
        response = self.client.call_action('get_user', email=user.primary_email)
        self.assertTrue(response.result.user.primary_email, user.primary_email)

    def test_get_user_no_email_specified_returns_current_user(self):
        response = self.client.call_action('get_user')
        self.assertTrue(response.result.user.primary_email, self.requester.primary_email)

    def test_get_user_email_wrong_organization(self):
        user = factories.UserFactory.create()
        with self.assertFieldError('email', 'DOES_NOT_EXIST'):
            self.client.call_action('get_user', email=user.primary_email)
