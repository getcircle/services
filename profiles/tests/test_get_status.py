import service.control

from services.test import (
    fuzzy,
    mocks,
    MockedTestCase,
)

from .. import factories


class TestProfiles(MockedTestCase):

    def setUp(self):
        super(TestProfiles, self).setUp()
        self.organization = mocks.mock_organization()
        self._mock_display_title()
        self.profile = factories.ProfileFactory.create_protobuf(
            organization_id=self.organization.id,
        )
        token = mocks.mock_token(
            profile_id=self.profile.id,
            organization_id=self.organization.id,
        )
        self.client = service.control.Client('profile', token=token)
        self.mock.instance.dont_mock_service('profile')

    def _mock_display_title(self):
        self.mock.instance.register_empty_response(
            service='organization',
            action='get_teams_for_profile_ids',
            mock_regex_lookup='organization:get_teams_for_profile_ids:.*',
        )

    def test_get_status_id_required(self):
        with self.assertFieldError('id', 'MISSING'):
            self.client.call_action('get_status')

    def test_get_status_does_not_exist(self):
        with self.assertFieldError('id', 'DOES_NOT_EXIST'):
            self.client.call_action('get_status', id=fuzzy.FuzzyUUID().fuzz())

    def test_get_status(self):
        profile = factories.ProfileFactory.create_protobuf(
            status={'value': 'some status'},
            organization_id=self.organization.id,
        )
        response = self.client.call_action('get_status', id=profile.status.id)

        status = response.result.status
        self.verify_containers(profile.status, status)
        self.assertEqual(profile.full_name, status.profile.full_name)

    def test_get_status_different_organization(self):
        profile = factories.ProfileFactory.create_protobuf(
            status={'value': 'some status'},
        )
        with self.assertFieldError('id', 'DOES_NOT_EXIST'):
            self.client.call_action('get_status', id=profile.status.id)
