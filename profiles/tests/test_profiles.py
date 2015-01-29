import datetime

from freezegun import freeze_time
from protobufs.profile_service_pb2 import ProfileService
import service.control
from service.transports import mock

from services.test import (
    fuzzy,
    mocks,
    TestCase,
)

from .. import factories


class TestProfiles(TestCase):

    def setUp(self):
        self.client = service.control.Client('profile', token='test-token')
        self.user_client = service.control.Client('user', token='test-token')
        self.org_client = service.control.Client(
            'organization',
            token='test-token',
        )
        self.profile_data = factories.ProfileFactory.get_protobuf_data()

    def _create_and_add_profile_to_team(self, team):
        self.client.call_action(
            'create_profile',
            profile=factories.ProfileFactory.get_protobuf_data(),
        )

    def _create_user(self):
        response = self.user_client.call_action(
            'create_user',
            email=fuzzy.FuzzyText(suffix='@example.com').fuzz(),
        )
        self.assertTrue(response.success)
        return response.result.user

    def _create_organization(self):
        response = self.org_client.call_action(
            'create_organization',
            organization={
                'name': fuzzy.FuzzyText().fuzz(),
                'domain': fuzzy.FuzzyText(suffix='.com').fuzz(),
            },
        )
        self.assertTrue(response.success)
        return response.result.organization

    def _create_address(self, organization=None):
        if not organization:
            organization = self._create_organization()

        address_data = {
            'organization_id': organization.id,
            'address_1': '319 Primrose',
            'city': 'Burlingame',
            'region': 'California',
            'postal_code': '94010',
            'country_code': 'US',
            'latitude': '37.578286',
            'longitude': '-122.348729',
        }
        response = self.org_client.call_action(
            'create_address',
            address=address_data,
        )
        self.assertTrue(response.success)
        return response.result.address

    def _create_team_and_owner(self, organization_id, address_id, child_of=None):
        user = self._create_user()
        response = self.org_client.call_action(
            'create_team',
            team={
                'organization_id': organization_id,
                'name': fuzzy.FuzzyText().fuzz(),
                'owner_id': user.id,
            },
            child_of=child_of,
        )
        self.assertTrue(response.success)
        team = response.result.team

        profile = factories.ProfileFactory.create_protobuf(
            user_id=user.id,
            organization_id=organization_id,
            address_id=address_id,
            team_id=team.id,
        )
        return team, profile

    def test_create_profile_invalid_organization_id(self):
        self.profile_data['organization_id'] = 'invalid'
        response = self.client.call_action(
            'create_profile',
            profile=self.profile_data,
        )
        self._verify_field_error(response, 'profile.organization_id')

    def test_create_profile_invalid_user_id(self):
        self.profile_data['user_id'] = 'invalid'
        response = self.client.call_action(
            'create_profile',
            profile=self.profile_data,
        )
        self._verify_field_error(response, 'profile.user_id')

    def test_create_profile_invalid_address_id(self):
        self.profile_data['address_id'] = 'invalid'
        response = self.client.call_action(
            'create_profile',
            profile=self.profile_data,
        )
        self._verify_field_error(response, 'profile.address_id')

    def test_create_profile_invalid_team_id(self):
        self.profile_data['team_id'] = 'invalid'
        response = self.client.call_action(
            'create_profile',
            profile=self.profile_data,
        )
        self._verify_field_error(response, 'profile.team_id')

    def test_create_profile(self):
        profile_data = factories.ProfileFactory.get_protobuf_data()
        response = self.client.call_action('create_profile', profile=profile_data)
        self.assertTrue(response.success)
        self._verify_container_matches_data(response.result.profile, profile_data)

    def test_get_profiles_invalid_organization_id(self):
        response = self.client.call_action(
            'get_profiles',
            organization_id='invalid',
        )
        self._verify_field_error(response, 'organization_id')

    def test_get_profiles_with_organization_id(self):
        profile = factories.ProfileFactory.create_protobuf()
        response = self.client.call_action(
            'get_profiles',
            organization_id=profile.organization_id,
        )
        self.assertTrue(response.success)
        self.assertEqual(len(response.result.profiles), 1)
        self._verify_containers(profile, response.result.profiles[0])

    def test_get_profiles_invalid_tag_id(self):
        response = self.client.call_action('get_profiles', tag_id='invalid')
        self._verify_field_error(response, 'tag_id')

    def test_get_profiles_tags(self):
        tag = factories.TagFactory.create()
        factories.ProfileFactory.create_batch(size=4, tags=[tag])
        response = self.client.call_action('get_profiles', tag_id=str(tag.id))
        self.assertTrue(response.success)
        self.assertEqual(len(response.result.profiles), 4)

    def test_get_profiles_invalid_team_id(self):
        response = self.client.call_action(
            'get_profiles',
            team_id='invalid',
        )
        self._verify_field_error(response, 'team_id')

    def _mock_get_direct_reports(self, user_id, profiles=2):
        service = 'profile'
        action = 'get_direct_reports'
        mock_response = mock.get_mockable_response(service, action)
        for _ in range(profiles):
            profile = mock_response.profiles.add()
            mocks.mock_profile(profile)
        mock.instance.register_mock_response(service, action, mock_response, user_id=user_id)

    def _mock_get_team(self, **overrides):
        service = 'organization'
        action = 'get_team'
        mock_response = mock.get_mockable_response(service, action)
        mocks.mock_team(mock_response.team, **overrides)
        mock.instance.register_mock_response(
            service,
            action,
            mock_response,
            team_id=mock_response.team.id,
        )
        return mock_response.team

    def test_get_profiles(self):
        team = self._mock_get_team()
        created_first = factories.ProfileFactory.create_protobuf(first_name='b', team_id=team.id)
        self._mock_get_direct_reports(team.owner_id, profiles=0)
        created_second = factories.ProfileFactory.create_protobuf(
            first_name='a',
            team_id=created_first.team_id,
        )
        factories.ProfileFactory.create_batch(
            size=2,
            first_name='z',
            team_id=created_first.team_id,
        )
        with mocks.mock_transport(self.client) as local_client:
            response = local_client.call_action(
                'get_profiles',
                team_id=created_second.team_id,
            )

        self.assertTrue(response.success)
        self.assertEqual(len(response.result.profiles), 4)
        # ensure results are sorted alphabetically
        self._verify_containers(created_second, response.result.profiles[0])
        self._verify_containers(created_first, response.result.profiles[1])

    def test_get_profiles_team_id_includes_owners_direct_reports(self):
        owner = factories.ProfileFactory.create_protobuf(first_name='owner')
        team = self._mock_get_team(id=owner.team_id, owner_id=owner.user_id)
        self._mock_get_team(owner_id=owner.id)
        factories.ProfileFactory.create_batch(size=2, team_id=owner.team_id)
        self._mock_get_direct_reports(team.owner_id)

        with mocks.mock_transport(self.client) as local_client:
            response = local_client.call_action('get_profiles', team_id=team.id)

        self.assertTrue(response.success)
        # should include owner, profiles with same team_id and any direct reports of owner
        self.assertEqual(len(response.result.profiles), 5)

    def test_get_profile(self):
        expected = factories.ProfileFactory.create_protobuf()
        response = self.client.call_action(
            'get_profile',
            profile_id=expected.id,
        )
        self._verify_containers(expected, response.result.profile)

    def test_get_profile_full_name(self):
        profile = factories.ProfileFactory.create_protobuf()
        self.assertTrue(profile.full_name)

    def test_get_profile_invalid_profile_id(self):
        response = self.client.call_action(
            'get_profile',
            profile_id='invalid',
        )
        self._verify_field_error(response, 'profile_id')

    def test_get_profile_does_not_exist(self):
        response = self.client.call_action(
            'get_profile',
            profile_id=fuzzy.FuzzyUUID().fuzz(),
        )
        self._verify_field_error(response, 'profile_id', 'DOES_NOT_EXIST')

    def test_update_profile_invalid_profile_id(self):
        self.profile_data['id'] = 'invalid'
        response = self.client.call_action('update_profile', profile=self.profile_data)
        self._verify_field_error(response, 'profile.id')

    def test_update_profile_does_not_exist(self):
        self.profile_data['id'] = fuzzy.FuzzyUUID().fuzz()
        response = self.client.call_action('update_profile', profile=self.profile_data)
        self._verify_field_error(response, 'profile.id', 'DOES_NOT_EXIST')

    def test_update_profile(self):
        original = factories.ProfileFactory.create_protobuf()
        profile = ProfileService.Containers.Profile()
        profile.CopyFrom(original)

        profile.first_name = 'Michael'
        profile.last_name = 'Hahn'
        profile.email = 'mwhahn@gmail.com'
        profile.cell_phone = '+19492931122'
        profile.title = 'Engineer'

        # this has no effect, this just makes validating the container easier
        profile.full_name = 'Michael Hahn'

        response = self.client.call_action('update_profile', profile=profile)
        self._verify_containers(profile, response.result.profile)

    def test_get_direct_reports_invalid_profile_id(self):
        response = self.client.call_action('get_direct_reports', profile_id='invalid')
        self._verify_field_error(response, 'profile_id')

    def test_get_direct_reports_profile_does_not_exist(self):
        response = self.client.call_action(
            'get_direct_reports',
            profile_id=fuzzy.FuzzyUUID().fuzz(),
        )
        self._verify_field_error(response, 'profile_id', 'DOES_NOT_EXIST')

    def test_get_peers_invalid_profile_id(self):
        response = self.client.call_action('get_peers', profile_id='invalid')
        self._verify_field_error(response, 'profile_id')

    def test_get_peers_profile_does_not_exist(self):
        response = self.client.call_action('get_peers', profile_id=fuzzy.FuzzyUUID().fuzz())
        self._verify_field_error(response, 'profile_id', 'DOES_NOT_EXIST')

    def test_get_direct_reports_invalid_user_id(self):
        response = self.client.call_action('get_direct_reports', user_id='invalid')
        self._verify_field_error(response, 'user_id')

    def _setup_direct_reports_test(self):
        address = self._create_address()

        # create a parent team and owner
        parent_team, owner = self._create_team_and_owner(address.organization_id, address.id)

        # create teams that children to the parent_team
        for _ in range(3):
            self._create_team_and_owner(
                address.organization_id,
                address.id,
                child_of=parent_team.id,
            )

        # add team members to the owners direct team
        for _ in range(3):
            factories.ProfileFactory.create(
                address_id=address.id,
                organization_id=address.organization_id,
                team_id=parent_team.id,
                user_id=self._create_user().id,
            )
        return owner

    def test_get_direct_reports(self):
        owner = self._setup_direct_reports_test()
        # direct reports for owner should be equal to the number of teams 1
        # level below as well as anyone directly on his team
        response = self.client.call_action('get_direct_reports', profile_id=owner.id)
        self.assertTrue(response.success)
        self.assertEqual(len(response.result.profiles), 6)

        # verify profiles are sorted by first_name, last_name
        sorted_profiles = sorted(
            response.result.profiles,
            key=lambda x: (x.first_name, x.last_name),
        )
        for index, profile in enumerate(response.result.profiles):
            self.assertEqual(profile, sorted_profiles[index])

    def test_get_direct_reports_user_id(self):
        owner = self._setup_direct_reports_test()
        response = self.client.call_action('get_direct_reports', user_id=owner.user_id)
        self.assertTrue(response.success)
        self.assertEqual(len(response.result.profiles), 6)

    def test_get_direct_reports_no_direct_reports(self):
        address = self._create_address()
        parent_team, _ = self._create_team_and_owner(address.organization_id, address.id)
        profile = factories.ProfileFactory.create_protobuf(
            organization_id=address.organization_id,
            address_id=address.id,
            team_id=parent_team.id,
        )

        response = self.client.call_action('get_direct_reports', profile_id=profile.id)
        self.assertTrue(response.success)
        self.assertEqual(len(response.result.profiles), 0)

    def test_get_peers_non_owner(self):
        address = self._create_address()
        parent_team, _ = self._create_team_and_owner(address.organization_id, address.id)

        for _ in range(3):
            peer = factories.ProfileFactory.create_protobuf(
                address_id=address.id,
                organization_id=address.organization_id,
                team_id=parent_team.id,
                user_id=self._create_user().id,
            )

        response = self.client.call_action('get_peers', profile_id=peer.id)
        self.assertTrue(response.success)
        self.assertEqual(len(response.result.profiles), 2)

    def test_get_peers(self):
        address = self._create_address()

        # create a parent team
        parent_team, _ = self._create_team_and_owner(address.organization_id, address.id)

        # create a sub-team we'll use as our test case
        team, _ = self._create_team_and_owner(
            address.organization_id,
            address.id,
            child_of=parent_team.id,
        )

        # create teams that are children of the one above
        for _ in range(3):
            _, peer = self._create_team_and_owner(
                address.organization_id,
                address.id,
                child_of=team.id,
            )

        response = self.client.call_action('get_peers', profile_id=peer.id)
        self.assertTrue(response.success)
        self.assertEqual(len(response.result.profiles), 2)

        # verify peers are sorted alphabetically by first_name, last_name
        sorted_profiles = sorted(
            response.result.profiles,
            key=lambda x: (x.first_name, x.last_name),
        )
        for index, profile in enumerate(response.result.profiles):
            self.assertEqual(sorted_profiles[index], profile)

    def test_get_peers_ceo(self):
        address = self._create_address()

        # create a root team
        _, owner = self._create_team_and_owner(address.organization_id, address.id)
        response = self.client.call_action('get_peers', profile_id=owner.id)
        self.assertTrue(response.success)
        self.assertEqual(len(response.result.profiles), 0)

    def test_get_peers_ceo_members_on_direct_team(self):
        address = self._create_address()

        # create a root team
        team, owner = self._create_team_and_owner(address.organization_id, address.id)

        # add someone on his direct team (C level exec)
        self._create_and_add_profile_to_team(team)

        response = self.client.call_action('get_peers', profile_id=owner.id)
        self.assertTrue(response.success)
        self.assertEqual(len(response.result.profiles), 0)

    def test_get_profile_stats_address_invalid(self):
        response = self.client.call_action('get_profile_stats', address_ids=['invalid'])
        self._verify_field_error(response, 'address_ids')

    def test_get_profile_stats_address_no_profiles(self):
        response = self.client.call_action(
            'get_profile_stats',
            address_ids=[fuzzy.FuzzyUUID().fuzz()],
        )
        self.assertTrue(response.success)
        stats = response.result.stats[0]
        self.assertEqual(stats.count, '0')

    def test_get_profile_stats_address(self):
        address_id = fuzzy.FuzzyUUID().fuzz()
        factories.ProfileFactory.create_batch(5, address_id=address_id)
        response = self.client.call_action('get_profile_stats', address_ids=[address_id])
        self.assertTrue(response.success)
        stats = response.result.stats[0]
        self.assertEqual(stats.count, '5')

    def test_create_profile_duplicate(self):
        profile = factories.ProfileFactory.create_protobuf()
        response = self.client.call_action('create_profile', profile=profile)
        self.assertFalse(response.success)
        self.assertIn('DUPLICATE', response.errors)

    def test_get_upcoming_anniversaries_invalid_organization_id(self):
        response = self.client.call_action('get_upcoming_anniversaries', organization_id='invalid')
        self._verify_field_error(response, 'organization_id')

    @freeze_time('2015-01-09')
    def test_get_upcoming_anniversaries(self):
        organization_id = fuzzy.FuzzyUUID().fuzz()
        # create a profile whose anniversary is in the past
        factories.ProfileFactory.create(
            hire_date=datetime.date(2014, 1, 8),
            organization_id=organization_id,
        )

        # create a profile with an upcoming anniversary
        factories.ProfileFactory.create(
            hire_date=datetime.date(2013, 1, 11),
            organization_id=organization_id,
        )
        factories.ProfileFactory.create(
            hire_date=datetime.date(2014, 1, 10),
            organization_id=organization_id,
        )
        response = self.client.call_action(
            'get_upcoming_anniversaries',
            organization_id=organization_id,
        )
        self.assertTrue(response.success)
        profiles = response.result.profiles
        self.assertEqual(len(profiles), 2)

        # verify the sort order
        self.assertEqual(profiles[0].hire_date, '2014-01-10')
        self.assertEqual(profiles[1].hire_date, '2013-01-11')

    @freeze_time('2015-01-09')
    def test_get_upcoming_anniversaries_all_in_future(self):
        organization_id = fuzzy.FuzzyUUID().fuzz()
        factories.ProfileFactory.create(
            hire_date=datetime.date(2015, 1, 9),
            organization_id=organization_id,
        )
        factories.ProfileFactory.create(
            hire_date=datetime.date(2015, 1, 10),
            organization_id=organization_id,
        )
        factories.ProfileFactory.create(
            hire_date=datetime.date(2015, 1, 11),
            organization_id=organization_id,
        )

        response = self.client.call_action(
            'get_upcoming_anniversaries',
            organization_id=organization_id,
        )
        self.assertTrue(response.success)
        self.assertEqual(len(response.result.profiles), 0)

    @freeze_time('2015-01-09')
    def test_get_upcoming_anniversaries_in_past_this_year(self):
        organization_id = fuzzy.FuzzyUUID().fuzz()
        factories.ProfileFactory.create(
            hire_date=datetime.date(2015, 1, 8),
            organization_id=organization_id,
        )
        factories.ProfileFactory.create(
            hire_date=datetime.date(2014, 12, 10),
            organization_id=organization_id,
        )

        response = self.client.call_action(
            'get_upcoming_anniversaries',
            organization_id=organization_id,
        )
        self.assertTrue(response.success)
        self.assertEqual(len(response.result.profiles), 0)

    @freeze_time('2014-12-31')
    def test_get_upcoming_anniversaries_end_of_month_end_of_year(self):
        organization_id = fuzzy.FuzzyUUID().fuzz()
        factories.ProfileFactory.create(
            hire_date=datetime.date(2012, 1, 1),
            organization_id=organization_id,
        )
        response = self.client.call_action(
            'get_upcoming_anniversaries',
            organization_id=organization_id,
        )
        self.assertTrue(response.success)
        self.assertEqual(len(response.result.profiles), 1)

    @freeze_time('2014-11-30')
    def test_get_upcoming_anniversaries_end_of_month(self):
        organization_id = fuzzy.FuzzyUUID().fuzz()
        # create an upcoming anniversary
        factories.ProfileFactory.create(
            hire_date=datetime.date(2012, 12, 1),
            organization_id=organization_id,
        )
        # create a past anniversary
        factories.ProfileFactory.create(
            hire_date=datetime.date(2012, 10, 1),
            organization_id=organization_id,
        )
        response = self.client.call_action(
            'get_upcoming_anniversaries',
            organization_id=organization_id,
        )
        self.assertTrue(response.success)
        self.assertEqual(len(response.result.profiles), 1)

    def test_get_upcoming_birthdays_invalid_organization_id(self):
        response = self.client.call_action('get_upcoming_birthdays', organization_id='invalid')
        self._verify_field_error(response, 'organization_id')

    @freeze_time('2015-01-09')
    def test_get_upcoming_birthdays(self):
        organization_id = fuzzy.FuzzyUUID().fuzz()
        factories.ProfileFactory.create(
            birth_date=datetime.date(1982, 1, 12),
            organization_id=organization_id,
        )
        factories.ProfileFactory.create(
            birth_date=datetime.date(1980, 1, 10),
            organization_id=organization_id,
        )
        response = self.client.call_action(
            'get_upcoming_birthdays',
            organization_id=organization_id,
        )
        self.assertTrue(response.success)
        profiles = response.result.profiles
        self.assertEqual(len(profiles), 2)

        # verify sort order
        self.assertEqual(profiles[0].birth_date, '1980-01-10')
        self.assertEqual(profiles[1].birth_date, '1982-01-12')

    @freeze_time('2014-12-31')
    def test_get_upcoming_birthdays_end_of_month_end_of_year(self):
        organization_id = fuzzy.FuzzyUUID().fuzz()
        factories.ProfileFactory.create(
            birth_date=datetime.date(1980, 1, 1),
            organization_id=organization_id,
        )
        response = self.client.call_action(
            'get_upcoming_birthdays',
            organization_id=organization_id,
        )
        self.assertTrue(response.success)
        self.assertEqual(len(response.result.profiles), 1)

    @freeze_time('2014-11-30')
    def test_get_upcoming_birthdays_end_of_month(self):
        organization_id = fuzzy.FuzzyUUID().fuzz()
        # create an upcoming anniversary
        factories.ProfileFactory.create(
            birth_date=datetime.date(2012, 12, 1),
            organization_id=organization_id,
        )
        # create a past anniversary
        factories.ProfileFactory.create(
            birth_date=datetime.date(2012, 10, 1),
            organization_id=organization_id,
        )
        response = self.client.call_action(
            'get_upcoming_birthdays',
            organization_id=organization_id,
        )
        self.assertTrue(response.success)
        self.assertEqual(len(response.result.profiles), 1)

    def test_get_recent_hires_invalid_organization_id(self):
        response = self.client.call_action('get_recent_hires', organization_id='invalid')
        self._verify_field_error(response, 'organization_id')

    @freeze_time('2015-01-10')
    def test_get_recent_hires(self):
        organization_id = fuzzy.FuzzyUUID().fuzz()
        factories.ProfileFactory.create(
            hire_date=datetime.date(2015, 1, 8),
            organization_id=organization_id,
        )
        factories.ProfileFactory.create(
            hire_date=datetime.date(2014, 12, 31),
            organization_id=organization_id,
        )
        response = self.client.call_action('get_recent_hires', organization_id=organization_id)
        self.assertTrue(response.success)
        self.assertEqual(len(response.result.profiles), 1)

    @freeze_time('2015-01-01')
    def test_get_recent_hires_beginning_of_year(self):
        organization_id = fuzzy.FuzzyUUID().fuzz()
        factories.ProfileFactory.create(
            hire_date=datetime.date(2014, 12, 31),
            organization_id=organization_id,
        )
        factories.ProfileFactory.create(
            hire_date=datetime.date(2014, 12, 30),
            organization_id=organization_id,
        )
        response = self.client.call_action('get_recent_hires', organization_id=organization_id)
        self.assertTrue(response.success)
        self.assertEqual(len(response.result.profiles), 2)

    @freeze_time('2014-12-01')
    def test_get_recent_hires_beginning_of_month(self):
        organization_id = fuzzy.FuzzyUUID().fuzz()
        factories.ProfileFactory.create(
            hire_date=datetime.date(2014, 11, 30),
            organization_id=organization_id,
        )
        response = self.client.call_action('get_recent_hires', organization_id=organization_id)
        self.assertTrue(response.success)
        self.assertEqual(len(response.result.profiles), 1)

    def test_get_active_tags_invalid_organization_id(self):
        response = self.client.call_action('get_active_tags', organization_id='invalid')
        self._verify_field_error(response, 'organization_id')

    def test_get_active_tags(self):
        tags = factories.TagFactory.create_batch(size=3)
        profile = factories.ProfileFactory.create(tags=[tags[1]])
        # add duplicate
        factories.ProfileFactory.create(tags=[tags[1]])
        response = self.client.call_action(
            'get_active_tags',
            organization_id=str(profile.organization_id),
        )
        self.assertTrue(response.success)
        self.assertEqual(len(response.result.tags), 1)

    def test_get_profiles_address_id_invalid(self):
        response = self.client.call_action('get_profiles', address_id='invalid')
        self._verify_field_error(response, 'address_id')

    def test_get_profiles_with_address_id(self):
        address = mocks.mock_address()
        factories.ProfileFactory.create_batch(
            size=5,
            address_id=address.id,
            organization_id=address.organization_id,
        )
        response = self.client.call_action('get_profiles', address_id=address.id)
        self.assertTrue(response.success)
        self.assertEqual(len(response.result.profiles), 5)

    def test_get_profiles_invalid_id_list(self):
        response = self.client.call_action('get_profiles', ids=['invalid'])
        self._verify_field_error(response, 'ids')

    def test_get_profiles_with_id_list(self):
        profiles = factories.ProfileFactory.create_batch(size=5)
        response = self.client.call_action(
            'get_profiles',
            ids=[str(profile.id) for profile in profiles],
        )
        self.assertTrue(response.success)
        self.assertEqual(len(response.result.profiles), 5)
