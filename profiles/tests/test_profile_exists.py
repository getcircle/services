import service.control

from services.test import (
    mocks,
    MockedTestCase,
)

from .. import factories


class TestProfiles(MockedTestCase):

    def setUp(self):
        super(TestProfiles, self).setUp()
        self.client = service.control.Client('profile')
        self.mock.instance.dont_mock_service('profile')
        self._mock_display_title()

    def _mock_display_title(self):
        self.mock.instance.register_empty_response(
            service='organization',
            action='get_teams_for_profile_ids',
            mock_regex_lookup='organization:get_teams_for_profile_ids:.*',
        )

    def test_profile_exists_email_required(self):
        with self.assertFieldError('email', 'MISSING'):
            self.client.call_action('profile_exists', domain='example')

    def test_profile_exists_organization_id_required(self):
        with self.assertFieldError('domain', 'MISSING'):
            self.client.call_action('profile_exists', email='me@example.com')

    def test_profile_exists_false(self):
        self.mock.instance.register_mock_object(
            service='organization',
            action='get_organization',
            return_object_path='organization',
            return_object=mocks.mock_organization(),
            domain='example',
        )
        response = self.client.call_action(
            'profile_exists',
            email='me@example.com',
            domain='example',
        )
        self.assertFalse(response.result.exists)

    def test_profile_exists_true(self):
        profile = factories.ProfileFactory.create()
        self.mock.instance.register_mock_object(
            service='organization',
            action='get_organization',
            return_object_path='organization',
            return_object=mocks.mock_organization(id=profile.organization_id),
            domain='example',
        )
        response = self.client.call_action('profile_exists', email=profile.email, domain='example')
        self.assertTrue(response.result.exists)
