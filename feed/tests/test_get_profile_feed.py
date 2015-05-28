import service.control
import service.settings
from service.transports import (
    local,
    mock,
)

from protobufs.services.feed import containers_pb2 as feed_containers
from protobufs.services.group import containers_pb2 as group_containers
from protobufs.services.profile import containers_pb2 as profile_containers

from services.test import (
    mocks,
    TestCase,
)


class TestGetCategories(TestCase):

    def setUp(self):
        service.settings.DEFAULT_TRANSPORT = 'service.transports.mock.instance'
        self.client = service.control.Client('feed', token='test-token')
        self.client.set_transport(local.instance)

    def tearDown(self):
        service.settings.DEFAULT_TRANSPORT = 'service.transports.local.instance'

    def _mock_action_profiles_response(self, service, action, profiles=3, **kwargs):
        mock_response = mock.get_mockable_response(service, action)
        for _ in range(profiles):
            profile = mock_response.profiles.add()
            mocks.mock_profile(profile)

        mock.instance.register_mock_response(service, action, mock_response, **kwargs)

    def _mock_get_profile(self, profile_id=None):
        service = 'profile'
        action = 'get_profile'
        mock_response = mock.get_mockable_response(service, action)
        mocks.mock_profile(mock_response.profile)
        if profile_id is not None:
            mock_response.profile.id = profile_id

        mock.instance.register_mock_response(
            service,
            action,
            mock_response,
            profile_id=mock_response.profile.id,
        )
        return mock_response.profile

    def _mock_get_peers(self, profile_id, peers=3):
        service = 'profile'
        action = 'get_peers'
        self._mock_action_profiles_response(service, action, profiles=peers, profile_id=profile_id)

    def _mock_get_direct_reports(self, profile_id, direct_reports=3):
        service = 'profile'
        action = 'get_direct_reports'
        self._mock_action_profiles_response(
            service,
            action,
            profiles=direct_reports,
            profile_id=profile_id,
        )

    def _mock_get_profile_stats(self, location_ids, count=3):
        service = 'profile'
        action = 'get_profile_stats'
        mock_response = mock.get_mockable_response(service, action)
        for location_id in location_ids:
            container = mock_response.stats.add()
            container.id = location_id
            container.count = count

        mock.instance.register_mock_response(
            service,
            action,
            mock_response,
            location_ids=location_ids,
        )

    def _mock_get_upcoming_anniversaries(self, organization_id, profiles=3):
        service = 'profile'
        action = 'get_upcoming_anniversaries'
        self._mock_action_profiles_response(
            service,
            action,
            profiles=profiles,
            organization_id=organization_id,
        )

    def _mock_get_upcoming_birthdays(self, organization_id, profiles=3):
        service = 'profile'
        action = 'get_upcoming_birthdays'
        self._mock_action_profiles_response(
            service,
            action,
            profiles=profiles,
            organization_id=organization_id,
        )

    def _mock_get_recent_hires(self, organization_id, profiles=3):
        service = 'profile'
        action = 'get_recent_hires'
        self._mock_action_profiles_response(
            service,
            action,
            profiles=profiles,
            organization_id=organization_id,
        )

    def _mock_get_active_tags(self, organization_id, tag_type, tags=3):
        service = 'profile'
        action = 'get_active_tags'

        mock_response = mock.get_mockable_response(service, action)
        for _ in range(tags):
            tag = mock_response.tags.add()
            mocks.mock_tag(tag)

        mock.instance.register_mock_response(
            service,
            action,
            mock_response,
            organization_id=organization_id,
            tag_type=tag_type,
        )

    def _mock_get_active_tags_skills(self, organization_id, tags=3):
        self._mock_get_active_tags(organization_id, profile_containers.TagV1.SKILL, tags=tags)

    def _mock_get_active_tags_interests(self, organization_id, tags=3):
        self._mock_get_active_tags(organization_id, profile_containers.TagV1.INTEREST, tags=tags)

    def _mock_get_notes(self, profile_id, notes=3):
        service = 'note'
        action = 'get_notes'

        mock_response = mock.get_mockable_response(service, action)
        for _ in range(notes):
            note = mock_response.notes.add()
            mocks.mock_note(note, owner_profile_id=profile_id)

        mock.instance.register_mock_response(
            service,
            action,
            mock_response,
            owner_profile_id=profile_id,
        )
        return mock_response.notes

    def _mock_get_profiles(self, profile_ids):
        service = 'profile'
        action = 'get_profiles'

        mock_response = mock.get_mockable_response(service, action)
        for profile_id in profile_ids:
            profile = mock_response.profiles.add()
            mocks.mock_profile(profile, id=profile_id)

        mock.instance.register_mock_response(
            service,
            action,
            mock_response,
            ids=profile_ids,
        )

    def _mock_get_membership_requests(self, profile_id, requests=3):
        service = 'group'
        action = 'get_membership_requests'

        mock_response = mock.get_mockable_response(service, action)
        for _ in range(requests):
            container = mock_response.requests.add()
            mocks.mock_group_membership_request(container, approver_profile_ids=[profile_id])

        # mock group calls as well
        mock_groups = mock.get_mockable_response(service, 'get_groups')
        for request in mock_response.requests:
            container = mock_groups.groups.add()
            mocks.mock_group(container, email=request.group_key)

        mock.instance.register_mock_response(
            service,
            action,
            mock_response,
        )
        mock.instance.register_mock_response(
            service,
            'get_groups',
            mock_groups,
            group_keys=[request.group_key for request in mock_response.requests],
            provider=group_containers.GOOGLE,
        )
        return mock_response.requests

    def test_profile_category_invalid_profile_id(self):
        with self.assertFieldError('profile_id'):
            self.client.call_action('get_profile_feed', profile_id='invalid')

    def test_peers_profile_category(self):
        profile = self._mock_get_profile()
        self._mock_get_peers(profile.id)
        self._mock_get_direct_reports(profile.id, direct_reports=0)
        self._mock_get_profile_stats([])
        self._mock_get_upcoming_anniversaries(profile.organization_id, profiles=0)
        self._mock_get_upcoming_birthdays(profile.organization_id, profiles=0)
        self._mock_get_recent_hires(profile.organization_id, profiles=0)
        self._mock_get_active_tags_skills(profile.organization_id, tags=0)
        self._mock_get_active_tags_interests(profile.organization_id, tags=0)
        self._mock_get_notes(profile.id, notes=0)
        self._mock_get_membership_requests(profile.id, requests=0)

        response = self.client.call_action('get_profile_feed', profile_id=profile.id)
        self.assertTrue(response.success)
        self.assertEqual(len(response.result.categories), 1)

        category = response.result.categories[0]
        self.assertEqual(category.title, 'Peers')
        self.assertEqual(len(category.profiles), 3)
        self.assertEqual(category.content_key, 'title')

    def test_direct_reports_profile_category(self):
        profile = self._mock_get_profile()
        self._mock_get_peers(profile.id, peers=0)
        self._mock_get_direct_reports(profile.id)
        self._mock_get_profile_stats([])
        self._mock_get_upcoming_anniversaries(profile.organization_id, profiles=0)
        self._mock_get_upcoming_birthdays(profile.organization_id, profiles=0)
        self._mock_get_recent_hires(profile.organization_id, profiles=0)
        self._mock_get_active_tags_skills(profile.organization_id, tags=0)
        self._mock_get_active_tags_interests(profile.organization_id, tags=0)
        self._mock_get_notes(profile.id, notes=0)
        self._mock_get_membership_requests(profile.id, requests=0)

        response = self.client.call_action('get_profile_feed', profile_id=profile.id)
        self.assertTrue(response.success)
        self.assertEqual(len(response.result.categories), 1)

        category = response.result.categories[0]
        self.assertEqual(category.title, 'Direct Reports')
        self.assertEqual(len(category.profiles), 3)
        self.assertEqual(category.content_key, 'title')
        self.assertEqual(category.category_type, feed_containers.CategoryV1.DIRECT_REPORTS)
        self.assertEqual(category.total_count, 3)

    def test_anniversaries_profile_category(self):
        profile = self._mock_get_profile()
        self._mock_get_peers(profile.id, peers=0)
        self._mock_get_direct_reports(profile.id, direct_reports=0)
        self._mock_get_profile_stats([])
        self._mock_get_upcoming_anniversaries(profile.organization_id)
        self._mock_get_upcoming_birthdays(profile.organization_id, profiles=0)
        self._mock_get_recent_hires(profile.organization_id, profiles=0)
        self._mock_get_membership_requests(profile.id, requests=0)

        self._mock_get_active_tags_skills(profile.organization_id, tags=0)
        self._mock_get_active_tags_interests(profile.organization_id, tags=0)
        self._mock_get_notes(profile.id, notes=0)

        response = self.client.call_action('get_profile_feed', profile_id=profile.id)
        self.assertTrue(response.success)
        self.assertEqual(len(response.result.categories), 1)

        category = response.result.categories[0]
        self.assertEqual(category.title, 'Work Anniversaries')
        self.assertEqual(len(category.profiles), 3)
        self.assertEqual(category.content_key, 'hire_date')
        self.assertEqual(category.category_type, feed_containers.CategoryV1.ANNIVERSARIES)
        self.assertEqual(category.total_count, 3)

    def test_birthdays_profile_category(self):
        profile = self._mock_get_profile()
        self._mock_get_peers(profile.id, peers=0)
        self._mock_get_direct_reports(profile.id, direct_reports=0)
        self._mock_get_profile_stats([])
        self._mock_get_upcoming_anniversaries(profile.organization_id, profiles=0)
        self._mock_get_upcoming_birthdays(profile.organization_id)
        self._mock_get_recent_hires(profile.organization_id, profiles=0)
        self._mock_get_active_tags_skills(profile.organization_id, tags=0)
        self._mock_get_active_tags_interests(profile.organization_id, tags=0)
        self._mock_get_notes(profile.id, notes=0)
        self._mock_get_membership_requests(profile.id, requests=0)

        response = self.client.call_action('get_profile_feed', profile_id=profile.id)
        self.assertTrue(response.success)
        self.assertEqual(len(response.result.categories), 1)

        category = response.result.categories[0]
        self.assertEqual(category.title, 'Birthdays')
        self.assertEqual(len(category.profiles), 3)
        self.assertEqual(category.content_key, 'birth_date')
        self.assertEqual(category.category_type, feed_containers.CategoryV1.BIRTHDAYS)
        self.assertEqual(category.total_count, 3)

    def test_recent_hires_profile_category(self):
        profile = self._mock_get_profile()
        self._mock_get_peers(profile.id, peers=0)
        self._mock_get_direct_reports(profile.id, direct_reports=0)
        self._mock_get_profile_stats([])
        self._mock_get_upcoming_anniversaries(profile.organization_id, profiles=0)
        self._mock_get_upcoming_birthdays(profile.organization_id, profiles=0)
        self._mock_get_recent_hires(profile.organization_id)
        self._mock_get_active_tags_skills(profile.organization_id, tags=0)
        self._mock_get_active_tags_interests(profile.organization_id, tags=0)
        self._mock_get_notes(profile.id, notes=0)
        self._mock_get_membership_requests(profile.id, requests=0)

        response = self.client.call_action('get_profile_feed', profile_id=profile.id)
        self.assertTrue(response.success)
        self.assertEqual(len(response.result.categories), 1)

        category = response.result.categories[0]
        self.assertEqual(category.title, 'New Hires')
        self.assertEqual(len(category.profiles), 3)
        self.assertEqual(category.content_key, 'hire_date')
        self.assertEqual(category.category_type, feed_containers.CategoryV1.NEW_HIRES)
        self.assertEqual(category.total_count, 3)

    def test_trending_tags_tag_category_interests(self):
        """Verify that trending interests show if we don't have active skills"""
        profile = self._mock_get_profile()
        # TODO we should have the mock transport return an error that the mock wasn't registred
        self._mock_get_peers(profile.id, peers=0)
        self._mock_get_direct_reports(profile.id, direct_reports=0)
        self._mock_get_profile_stats([])
        self._mock_get_upcoming_anniversaries(profile.organization_id, profiles=0)
        self._mock_get_upcoming_birthdays(profile.organization_id, profiles=0)
        self._mock_get_recent_hires(profile.organization_id, profiles=0)
        self._mock_get_active_tags_skills(profile.organization_id, tags=0)
        self._mock_get_active_tags_interests(profile.organization_id)
        self._mock_get_notes(profile.id, notes=0)
        self._mock_get_membership_requests(profile.id, requests=0)

        response = self.client.call_action('get_profile_feed', profile_id=profile.id)
        self.assertTrue(response.success)
        self.assertEqual(len(response.result.categories), 1)

        category = response.result.categories[0]
        self.assertEqual(category.title, 'Interests')
        self.assertEqual(len(category.tags), 3)
        self.assertEqual(category.content_key, 'name')
        self.assertEqual(category.category_type, feed_containers.CategoryV1.INTERESTS)

    def test_trending_tags_tag_category_skills(self):
        """Verify that trending skills instead of interests if we have them"""
        profile = self._mock_get_profile()
        self._mock_get_peers(profile.id, peers=0)
        self._mock_get_direct_reports(profile.id, direct_reports=0)
        self._mock_get_profile_stats([])
        self._mock_get_upcoming_anniversaries(profile.organization_id, profiles=0)
        self._mock_get_upcoming_birthdays(profile.organization_id, profiles=0)
        self._mock_get_recent_hires(profile.organization_id, profiles=0)
        self._mock_get_active_tags_skills(profile.organization_id)
        self._mock_get_active_tags_interests(profile.organization_id, tags=0)
        self._mock_get_notes(profile.id, notes=0)
        self._mock_get_membership_requests(profile.id, requests=0)

        response = self.client.call_action('get_profile_feed', profile_id=profile.id)
        self.assertTrue(response.success)
        self.assertEqual(len(response.result.categories), 1)

        category = response.result.categories[0]
        self.assertEqual(category.title, 'Skills')
        self.assertEqual(len(category.tags), 3)
        self.assertEqual(category.content_key, 'name')
        self.assertEqual(category.category_type, feed_containers.CategoryV1.SKILLS)

    def test_notes_note_category(self):
        profile = self._mock_get_profile()
        self._mock_get_peers(profile.id, peers=0)
        self._mock_get_direct_reports(profile.id, direct_reports=0)
        self._mock_get_profile_stats([])
        self._mock_get_upcoming_anniversaries(profile.organization_id, profiles=0)
        self._mock_get_upcoming_birthdays(profile.organization_id, profiles=0)
        self._mock_get_recent_hires(profile.organization_id, profiles=0)
        self._mock_get_active_tags_skills(profile.organization_id, tags=0)
        self._mock_get_active_tags_interests(profile.organization_id, tags=0)
        notes = self._mock_get_notes(profile.id)
        self._mock_get_profiles([note.for_profile_id for note in notes])
        self._mock_get_membership_requests(profile.id, requests=0)

        response = self.client.call_action('get_profile_feed', profile_id=profile.id)
        self.assertTrue(response.success)
        self.assertEqual(len(response.result.categories), 1)

        category = response.result.categories[0]
        self.assertEqual(category.title, 'Notes')
        self.assertEqual(len(category.notes), 3)
        self.assertEqual(category.content_key, 'changed')
        self.assertEqual(category.category_type, feed_containers.CategoryV1.NOTES)
        self.assertEqual(category.total_count, 3)

    def test_group_membership_requests_category(self):
        profile = self._mock_get_profile()
        self._mock_get_peers(profile.id, peers=0)
        self._mock_get_direct_reports(profile.id, direct_reports=0)
        self._mock_get_profile_stats([])
        self._mock_get_upcoming_anniversaries(profile.organization_id, profiles=0)
        self._mock_get_upcoming_birthdays(profile.organization_id, profiles=0)
        self._mock_get_recent_hires(profile.organization_id, profiles=0)
        self._mock_get_active_tags_skills(profile.organization_id, tags=0)
        self._mock_get_active_tags_interests(profile.organization_id, tags=0)
        self._mock_get_notes(profile.id, notes=0)
        requests = self._mock_get_membership_requests(profile.id)
        self._mock_get_profiles([request.requester_profile_id for request in requests])

        response = self.client.call_action('get_profile_feed', profile_id=profile.id)
        self.assertTrue(response.success)
        self.assertEqual(len(response.result.categories), 1)

        category = response.result.categories[0]
        self.assertEqual(category.title, 'Group Membership Requests')
        self.assertEqual(len(category.group_membership_requests), 3)
        self.assertEqual(category.content_key, 'requester_profile_id')
        self.assertEqual(
            category.category_type,
            feed_containers.CategoryV1.GROUP_MEMBERSHIP_REQUESTS,
        )
        self.assertEqual(category.total_count, 3)
