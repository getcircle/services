import service.control
import service.settings
from service.transports import (
    local,
    mock,
)

from protobufs.landing_service_pb2 import LandingService

from services.test import (
    fuzzy,
    mocks,
    TestCase,
)


class TestGetCategories(TestCase):

    def setUp(self):
        service.settings.DEFAULT_TRANSPORT = 'service.transports.mock.instance'
        self.client = service.control.Client('landing', token='test-token')
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

    def _mock_get_addresses(self, organization_id, addresses=3):
        service = 'organization'
        action = 'get_addresses'
        mock_response = mock.get_mockable_response(service, action)
        address_list = []
        for _ in range(addresses):
            address = mock_response.addresses.add()
            address_list.append(mocks.mock_address(address))

        mock.instance.register_mock_response(
            service,
            action,
            mock_response,
            organization_id=organization_id,
        )
        return address_list

    def _mock_get_profile_stats(self, address_ids, count=3):
        service = 'profile'
        action = 'get_profile_stats'
        mock_response = mock.get_mockable_response(service, action)
        for address_id in address_ids:
            container = mock_response.stats.add()
            container.id = address_id
            container.count = str(count)

        mock.instance.register_mock_response(
            service,
            action,
            mock_response,
            address_ids=address_ids,
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

    def _mock_get_active_skills(self, organization_id, skills=3):
        service = 'profile'
        action = 'get_active_skills'

        mock_response = mock.get_mockable_response(service, action)
        for _ in range(skills):
            skill = mock_response.skills.add()
            skill.id = fuzzy.FuzzyUUID().fuzz()
            skill.name = fuzzy.FuzzyText().fuzz()

        mock.instance.register_mock_response(
            service,
            action,
            mock_response,
            organization_id=organization_id,
        )

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

    def test_profile_category_invalid_profile_id(self):
        with self.assertFieldError('profile_id'):
            self.client.call_action('get_categories', profile_id='invalid')

    def test_peers_profile_category(self):
        profile = self._mock_get_profile()
        self._mock_get_peers(profile.id)
        self._mock_get_direct_reports(profile.id, direct_reports=0)
        self._mock_get_addresses(profile.organization_id, addresses=0)
        self._mock_get_profile_stats([])
        self._mock_get_upcoming_anniversaries(profile.organization_id, profiles=0)
        self._mock_get_upcoming_birthdays(profile.organization_id, profiles=0)
        self._mock_get_recent_hires(profile.organization_id, profiles=0)
        self._mock_get_active_skills(profile.organization_id, skills=0)
        self._mock_get_notes(profile.id, notes=0)

        response = self.client.call_action('get_categories', profile_id=profile.id)
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
        self._mock_get_addresses(profile.organization_id, addresses=0)
        self._mock_get_profile_stats([])
        self._mock_get_upcoming_anniversaries(profile.organization_id, profiles=0)
        self._mock_get_upcoming_birthdays(profile.organization_id, profiles=0)
        self._mock_get_recent_hires(profile.organization_id, profiles=0)
        self._mock_get_active_skills(profile.organization_id, skills=0)
        self._mock_get_notes(profile.id, notes=0)

        response = self.client.call_action('get_categories', profile_id=profile.id)
        self.assertTrue(response.success)
        self.assertEqual(len(response.result.categories), 1)

        category = response.result.categories[0]
        self.assertEqual(category.title, 'Direct Reports')
        self.assertEqual(len(category.profiles), 3)
        self.assertEqual(category.content_key, 'title')
        self.assertEqual(category.type, LandingService.Containers.Category.DIRECT_REPORTS)
        self.assertEqual(category.total_count, str(3))

    def test_locations_address_category(self):
        profile = self._mock_get_profile()
        self._mock_get_peers(profile.id, peers=0)
        self._mock_get_direct_reports(profile.id, direct_reports=0)
        addresses = self._mock_get_addresses(profile.organization_id)
        self._mock_get_profile_stats([a.id for a in addresses])
        self._mock_get_upcoming_anniversaries(profile.organization_id, profiles=0)
        self._mock_get_upcoming_birthdays(profile.organization_id, profiles=0)
        self._mock_get_recent_hires(profile.organization_id, profiles=0)
        self._mock_get_active_skills(profile.organization_id, skills=0)
        self._mock_get_notes(profile.id, notes=0)

        response = self.client.call_action('get_categories', profile_id=profile.id)
        self.assertTrue(response.success)
        self.assertEqual(len(response.result.categories), 1)

        category = response.result.categories[0]
        self.assertEqual(category.title, 'Locations')
        self.assertEqual(len(category.addresses), 3)
        self.assertEqual(category.content_key, 'address_1')
        self.assertEqual(category.type, LandingService.Containers.Category.LOCATIONS)
        self.assertEqual(category.total_count, str(3))
        for address in category.addresses:
            self.assertEqual(address.profile_count, '3')

    def test_anniversaries_profile_category(self):
        profile = self._mock_get_profile()
        self._mock_get_peers(profile.id, peers=0)
        self._mock_get_direct_reports(profile.id, direct_reports=0)
        self._mock_get_addresses(profile.organization_id, addresses=0)
        self._mock_get_profile_stats([])
        self._mock_get_upcoming_anniversaries(profile.organization_id)
        self._mock_get_upcoming_birthdays(profile.organization_id, profiles=0)
        self._mock_get_recent_hires(profile.organization_id, profiles=0)
        self._mock_get_active_skills(profile.organization_id, skills=0)
        self._mock_get_notes(profile.id, notes=0)

        response = self.client.call_action('get_categories', profile_id=profile.id)
        self.assertTrue(response.success)
        self.assertEqual(len(response.result.categories), 1)

        category = response.result.categories[0]
        self.assertEqual(category.title, 'Work Anniversaries')
        self.assertEqual(len(category.profiles), 3)
        self.assertEqual(category.content_key, 'hire_date')
        self.assertEqual(category.type, LandingService.Containers.Category.ANNIVERSARIES)
        self.assertEqual(category.total_count, str(3))

    def test_birthdays_profile_category(self):
        profile = self._mock_get_profile()
        self._mock_get_peers(profile.id, peers=0)
        self._mock_get_direct_reports(profile.id, direct_reports=0)
        self._mock_get_addresses(profile.organization_id, addresses=0)
        self._mock_get_profile_stats([])
        self._mock_get_upcoming_anniversaries(profile.organization_id, profiles=0)
        self._mock_get_upcoming_birthdays(profile.organization_id)
        self._mock_get_recent_hires(profile.organization_id, profiles=0)
        self._mock_get_active_skills(profile.organization_id, skills=0)
        self._mock_get_notes(profile.id, notes=0)

        response = self.client.call_action('get_categories', profile_id=profile.id)
        self.assertTrue(response.success)
        self.assertEqual(len(response.result.categories), 1)

        category = response.result.categories[0]
        self.assertEqual(category.title, 'Birthdays')
        self.assertEqual(len(category.profiles), 3)
        self.assertEqual(category.content_key, 'birth_date')
        self.assertEqual(category.type, LandingService.Containers.Category.BIRTHDAYS)
        self.assertEqual(category.total_count, str(3))

    def test_recent_hires_profile_category(self):
        profile = self._mock_get_profile()
        self._mock_get_peers(profile.id, peers=0)
        self._mock_get_direct_reports(profile.id, direct_reports=0)
        self._mock_get_addresses(profile.organization_id, addresses=0)
        self._mock_get_profile_stats([])
        self._mock_get_upcoming_anniversaries(profile.organization_id, profiles=0)
        self._mock_get_upcoming_birthdays(profile.organization_id, profiles=0)
        self._mock_get_recent_hires(profile.organization_id)
        self._mock_get_active_skills(profile.organization_id, skills=0)
        self._mock_get_notes(profile.id, notes=0)

        response = self.client.call_action('get_categories', profile_id=profile.id)
        self.assertTrue(response.success)
        self.assertEqual(len(response.result.categories), 1)

        category = response.result.categories[0]
        self.assertEqual(category.title, 'New Hires')
        self.assertEqual(len(category.profiles), 3)
        self.assertEqual(category.content_key, 'hire_date')
        self.assertEqual(category.type, LandingService.Containers.Category.NEW_HIRES)
        self.assertEqual(category.total_count, str(3))

    def test_trending_skills_skill_category(self):
        profile = self._mock_get_profile()
        # TODO we should have the mock transport return an error that the mock wasn't registred
        self._mock_get_peers(profile.id, peers=0)
        self._mock_get_direct_reports(profile.id, direct_reports=0)
        self._mock_get_addresses(profile.organization_id, addresses=0)
        self._mock_get_profile_stats([])
        self._mock_get_upcoming_anniversaries(profile.organization_id, profiles=0)
        self._mock_get_upcoming_birthdays(profile.organization_id, profiles=0)
        self._mock_get_recent_hires(profile.organization_id, profiles=0)
        self._mock_get_active_skills(profile.organization_id)
        self._mock_get_notes(profile.id, notes=0)

        response = self.client.call_action('get_categories', profile_id=profile.id)
        self.assertTrue(response.success)
        self.assertEqual(len(response.result.categories), 1)

        category = response.result.categories[0]
        self.assertEqual(category.title, 'Skills')
        self.assertEqual(len(category.skills), 3)
        self.assertEqual(category.content_key, 'name')
        self.assertEqual(category.type, LandingService.Containers.Category.SKILLS)
        self.assertEqual(category.total_count, str(3))

    def test_notes_note_category(self):
        profile = self._mock_get_profile()
        self._mock_get_peers(profile.id, peers=0)
        self._mock_get_direct_reports(profile.id, direct_reports=0)
        self._mock_get_addresses(profile.organization_id, addresses=0)
        self._mock_get_profile_stats([])
        self._mock_get_upcoming_anniversaries(profile.organization_id, profiles=0)
        self._mock_get_upcoming_birthdays(profile.organization_id, profiles=0)
        self._mock_get_recent_hires(profile.organization_id, profiles=0)
        self._mock_get_active_skills(profile.organization_id, skills=0)
        notes = self._mock_get_notes(profile.id)
        self._mock_get_profiles([note.for_profile_id for note in notes])

        response = self.client.call_action('get_categories', profile_id=profile.id)
        self.assertTrue(response.success)
        self.assertEqual(len(response.result.categories), 1)

        category = response.result.categories[0]
        self.assertEqual(category.title, 'Notes')
        self.assertEqual(len(category.notes), 3)
        self.assertEqual(category.content_key, 'changed')
        self.assertEqual(category.type, LandingService.Containers.Category.NOTES)
        self.assertEqual(category.total_count, str(3))
