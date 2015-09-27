import service.control

from services.test import (
    fuzzy,
    MockedTestCase,
)

from .. import factories


class TestProfiles(MockedTestCase):

    def setUp(self):
        super(TestProfiles, self).setUp()
        self.client = service.control.Client('profile')
        self.mock.instance.dont_mock_service('profile')

    def test_profile_exists_email_required(self):
        with self.assertFieldError('email', 'MISSING'):
            self.client.call_action('profile_exists', organization_id=fuzzy.FuzzyUUID().fuzz())

    def test_profile_exists_organization_id_required(self):
        with self.assertFieldError('organization_id', 'MISSING'):
            self.client.call_action('profile_exists', email='me@example.com')

    def test_profile_exists_false(self):
        response = self.client.call_action(
            'profile_exists',
            email='me@example.com',
            organization_id=fuzzy.FuzzyUUID().fuzz(),
        )
        self.assertFalse(response.result.exists)

    def test_profile_exists_true(self):
        profile = factories.ProfileFactory.create()
        response = self.client.call_action(
            'profile_exists',
            email=profile.email,
            organization_id=profile.organization_id,
        )
        self.assertTrue(response.result.exists)
