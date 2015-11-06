import service.control

from services.test import (
    mocks,
    MockedTestCase,
)


class TestGetFlags(MockedTestCase):

    def setUp(self):
        super(TestGetFlags, self).setUp()
        self.organization = mocks.mock_organization()
        token = mocks.mock_token(organization_id=self.organization.id)
        self.client = service.control.Client('feature', token=token)
        self.mock.instance.register_mock_object(
            service='organization',
            action='get_organization',
            return_object=self.organization,
            return_object_path='organization',
        )
        self.mock.instance.dont_mock_service('feature')

    def test_feature_get_flags(self):
        with self.settings(FEATURE_SERVICE_POSTS_ENABLED_ORGANIZATIONS=[self.organization.domain]):
            response = self.client.call_action('get_flags')

        flags = response.result.flags
        self.assertTrue(flags.get('posts'))

        response = self.client.call_action('get_flags')
        flags = response.result.flags
        self.assertFalse(flags.get('posts'))
