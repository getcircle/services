import datetime
import uuid

from freezegun import freeze_time
from protobufs.services.profile import containers_pb2 as profile_containers
import service.control

from services.test import (
    fuzzy,
    mocks,
    TestCase,
)

from .. import factories


class TestProfiles(TestCase):

    def setUp(self):
        self.profile = factories.ProfileFactory.create_protobuf()
        token = mocks.mock_token(
            profile_id=self.profile.id,
            organization_id=self.profile.organization_id,
        )
        self.client = service.control.Client('profile', token=token)

    def test_create_profile_invalid_organization_id(self):
        self.profile.organization_id = 'invalid'
        with self.assertFieldError('profile.organization_id'):
            self.client.call_action(
                'create_profile',
                profile=self.profile,
            )

    def test_create_profile_invalid_user_id(self):
        self.profile.user_id = 'invalid'
        with self.assertFieldError('profile.user_id'):
            self.client.call_action(
                'create_profile',
                profile=self.profile,
            )

    def test_create_profile_invalid_address_id(self):
        self.profile.address_id = 'invalid'
        with self.assertFieldError('profile.address_id'):
            self.client.call_action(
                'create_profile',
                profile=self.profile,
            )

    def test_create_profile_invalid_team_id(self):
        self.profile.team_id = 'invalid'
        with self.assertFieldError('profile.team_id'):
            self.client.call_action(
                'create_profile',
                profile=self.profile,
            )

    def test_create_profile(self):
        profile_data = factories.ProfileFactory.get_protobuf_data()
        response = self.client.call_action('create_profile', profile=profile_data)
        self.assertTrue(response.success)
        self.assertFalse(response.result.profile.is_admin)
        self.verify_container_matches_data(response.result.profile, profile_data)

    def test_create_profile_admin(self):
        profile_data = factories.ProfileFactory.get_protobuf_data()
        profile_data['is_admin'] = True
        response = self.client.call_action('create_profile', profile=profile_data)
        self.assertTrue(response.result.profile.is_admin)

    def test_create_profile_about_empty_string_ignored(self):
        profile_data = factories.ProfileFactory.get_protobuf_data()
        profile_data['about'] = ''
        response = self.client.call_action('create_profile', profile=profile_data)
        self.assertFalse(response.result.profile.HasField('about'))

    def test_get_profiles_invalid_organization_id(self):
        with self.assertFieldError('organization_id'):
            self.client.call_action(
                'get_profiles',
                organization_id='invalid',
            )

    def test_get_profiles_organization_id_by_default(self):
        response = self.client.call_action('get_profiles')
        self.assertTrue(response.success)
        self.assertEqual(len(response.result.profiles), 1)
        self.verify_containers(self.profile, response.result.profiles[0])

    def test_get_profiles_invalid_tag_id(self):
        with self.assertFieldError('tag_id'):
            self.client.call_action('get_profiles', tag_id='invalid')

    def test_get_profiles_skills(self):
        skill = factories.TagFactory.create(organization_id=self.profile.organization_id)
        factories.ProfileFactory.create_batch(
            size=4,
            tags=[skill],
            organization_id=self.profile.organization_id,
        )
        response = self.client.call_action(
            'get_profiles',
            tag_id=str(skill.id),
        )
        self.assertEqual(len(response.result.profiles), 4)

    def test_get_profiles_invalid_team_id(self):
        with self.assertFieldError('team_id'):
            self.client.call_action(
                'get_profiles',
                team_id='invalid',
            )

    def _mock_get_direct_reports(self, mock, user_id, profiles=2):
        service = 'profile'
        action = 'get_direct_reports'
        mock_response = mock.get_mockable_response(service, action)
        for _ in range(profiles):
            profile = mock_response.profiles.add()
            mocks.mock_profile(profile)
        mock.instance.register_mock_response(service, action, mock_response, user_id=user_id)

    def _mock_get_team(self, mock, **overrides):
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

    def _mock_get_team_descendants(self, mock, team_id, children_ids):
        service = 'organization'
        action = 'get_team_descendants'
        mock_response = mock.get_mockable_response(service, action)
        descendants = mock_response.descendants.add()
        descendants.parent_team_id = team_id
        for child_id in children_ids:
            team = descendants.teams.add()
            mocks.mock_team(team, id=child_id)
        mock.instance.register_mock_response(
            service,
            action,
            mock_response,
            team_ids=[team_id],
            attributes=['id'],
        )

    def test_get_profiles(self):
        with self.mock_transport(self.client) as mock:
            team = self._mock_get_team(mock)
            created_first = factories.ProfileFactory.create_protobuf(
                first_name='b',
                team_id=team.id,
            )
            self._mock_get_direct_reports(mock, team.owner_id, profiles=0)
            created_second = factories.ProfileFactory.create_protobuf(
                first_name='a',
                team_id=created_first.team_id,
            )
            factories.ProfileFactory.create_batch(
                size=2,
                first_name='z',
                team_id=created_first.team_id,
            )
            response = self.client.call_action(
                'get_profiles',
                team_id=created_second.team_id,
            )

        self.assertTrue(response.success)
        self.assertEqual(len(response.result.profiles), 4)
        # ensure results are sorted alphabetically
        self.verify_containers(created_second, response.result.profiles[0])
        self.verify_containers(created_first, response.result.profiles[1])

    def test_get_profiles_team_id_includes_owners_direct_reports(self):
        owner = factories.ProfileFactory.create_protobuf(first_name='owner')
        factories.ProfileFactory.create_batch(size=2, team_id=owner.team_id)

        with self.mock_transport(self.client) as mock:
            team = self._mock_get_team(mock, id=owner.team_id, owner_id=owner.user_id)
            self._mock_get_team(mock, owner_id=owner.id)
            self._mock_get_direct_reports(mock, team.owner_id)
            response = self.client.call_action('get_profiles', team_id=team.id)

        self.assertTrue(response.success)
        # should include owner, profiles with same team_id and any direct reports of owner
        self.assertEqual(len(response.result.profiles), 5)

    def test_get_profile(self):
        expected = factories.ProfileFactory.create_protobuf()
        response = self.client.call_action(
            'get_profile',
            profile_id=expected.id,
        )
        self.verify_containers(expected, response.result.profile)

    def test_get_profile_full_name(self):
        profile = factories.ProfileFactory.create_protobuf()
        self.assertTrue(profile.full_name)

    def test_get_profile_invalid_profile_id(self):
        with self.assertFieldError('profile_id'):
            self.client.call_action(
                'get_profile',
                profile_id='invalid',
            )

    def test_get_profile_does_not_exist(self):
        with self.assertFieldError('profile_id', 'DOES_NOT_EXIST'):
            self.client.call_action(
                'get_profile',
                profile_id=fuzzy.FuzzyUUID().fuzz(),
            )

    def test_update_profile_invalid_profile_id(self):
        self.profile.id = 'invalid'
        with self.assertFieldError('profile.id'):
            self.client.call_action('update_profile', profile=self.profile)

    def test_update_profile_does_not_exist(self):
        self.profile.id = fuzzy.FuzzyUUID().fuzz()
        with self.assertFieldError('profile.id', 'DOES_NOT_EXIST'):
            self.client.call_action('update_profile', profile=self.profile)

    def test_update_profile(self):
        original = factories.ProfileFactory.create_protobuf()
        profile = profile_containers.ProfileV1()
        profile.CopyFrom(original)

        profile.first_name = 'Michael'
        profile.last_name = 'Hahn'
        profile.title = 'Engineer'

        # this has no effect, this just makes validating the container easier
        profile.full_name = 'Michael Hahn'

        response = self.client.call_action('update_profile', profile=profile)
        self.verify_containers(profile, response.result.profile)

    def test_get_direct_reports_invalid_profile_id(self):
        with self.assertFieldError('profile_id'):
            self.client.call_action('get_direct_reports', profile_id='invalid')

    def test_get_direct_reports_profile_does_not_exist(self):
        with self.assertFieldError('profile_id', 'DOES_NOT_EXIST'):
            self.client.call_action(
                'get_direct_reports',
                profile_id=fuzzy.FuzzyUUID().fuzz(),
            )

    def test_get_peers_invalid_profile_id(self):
        with self.assertFieldError('profile_id'):
            self.client.call_action('get_peers', profile_id='invalid')

    def test_get_peers_profile_does_not_exist(self):
        with self.assertFieldError('profile_id', 'DOES_NOT_EXIST'):
            self.client.call_action('get_peers', profile_id=fuzzy.FuzzyUUID().fuzz())

    def test_get_direct_reports_invalid_user_id(self):
        with self.assertFieldError('user_id'):
            self.client.call_action('get_direct_reports', user_id='invalid')

    def _setup_direct_reports_test(self):
        address = self._create_address()

        # create a parent team and owner
        parent_team, owner = self._create_team_and_owner(address.organization_id, address.id)

        # create teams that children to the parent_team
        for _ in range(3):
            team, sub_owner = self._create_team_and_owner(
                address.organization_id,
                address.id,
                child_of=parent_team.id,
            )

            # add sub teams
            for _ in range(2):
                self._create_team_and_owner(
                    address.organization_id,
                    address.id,
                    child_of=team.id,
                )

            # add members to these sub teams
            factories.ProfileFactory.create(
                address_id=address.id,
                organization_id=address.organization_id,
                team_id=team.id,
                user_id=self._create_user().id,
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
        # direct reports for owner should be equal to the number of teams 1
        # level below as well as anyone directly on his team
        parent_team = mocks.mock_team(
            owner_id=self.profile.user_id,
            organization_id=self.profile.organization_id,
        )
        descendant = mocks.mock_team_descendants(
            parent_team_id=parent_team.id,
        )
        factories.ProfileFactory.create(
            user_id=descendant.teams[0].owner_id,
            organization_id=parent_team.organization_id,
        )

        with self.mock_transport() as mock:
            mock.instance.register_mock_object(
                service='organization',
                action='get_team',
                return_object_path='team',
                return_object=parent_team,
                mock_regex_lookup='organization:get_team:.*',
            )
            mock.instance.register_mock_object(
                service='organization',
                action='get_team_descendants',
                return_object_path='descendants',
                return_object=[descendant],
                mock_regex_lookup='organization:get_team_descendants:.*',
            )
            response = self.client.call_action('get_direct_reports', profile_id=self.profile.id)
        self.assertTrue(response.success)
        self.assertEqual(len(response.result.profiles), 1)

        # verify profiles are case-insensitive sorted by first_name, last_name
        sorted_profiles = sorted(
            response.result.profiles,
            key=lambda x: (x.first_name.lower(), x.last_name.lower()),
        )
        for index, profile in enumerate(response.result.profiles):
            self.verify_containers(profile, sorted_profiles[index])

    def test_get_direct_reports_user_id(self):
        parent_team = mocks.mock_team(
            owner_id=self.profile.user_id,
            organization_id=self.profile.organization_id,
        )
        descendant = mocks.mock_team_descendants(
            parent_team_id=parent_team.id,
        )
        factories.ProfileFactory.create(
            user_id=descendant.teams[0].owner_id,
            organization_id=parent_team.organization_id,
        )
        factories.ProfileFactory.create(
            organization_id=parent_team.organization_id,
            team_id=parent_team.id,
        )

        with self.mock_transport() as mock:
            mock.instance.register_mock_object(
                service='organization',
                action='get_team',
                return_object_path='team',
                return_object=parent_team,
                mock_regex_lookup='organization:get_team:.*',
            )
            mock.instance.register_mock_object(
                service='organization',
                action='get_team_descendants',
                return_object_path='descendants',
                return_object=[descendant],
                mock_regex_lookup='organization:get_team_descendants:.*',
            )
            response = self.client.call_action('get_direct_reports', profile_id=self.profile.id)
        self.assertEqual(len(response.result.profiles), 2)

    def test_get_direct_reports_no_direct_reports(self):
        parent_team = mocks.mock_team(
            owner_id=self.profile.user_id,
            organization_id=self.profile.organization_id,
        )

        with self.mock_transport() as mock:
            mock.instance.register_mock_object(
                service='organization',
                action='get_team',
                return_object_path='team',
                return_object=parent_team,
                mock_regex_lookup='organization:get_team:.*',
            )
            mock.instance.register_mock_object(
                service='organization',
                action='get_team_descendants',
                return_object_path='descendants',
                return_object=[],
                mock_regex_lookup='organization:get_team_descendants:.*',
            )
            response = self.client.call_action('get_direct_reports', profile_id=self.profile.id)
        self.assertTrue(response.success)
        self.assertEqual(len(response.result.profiles), 0)

    def test_get_peers_non_owner(self):
        team = mocks.mock_team(
            id=self.profile.team_id,
            organization_id=self.profile.organization_id,
        )
        peers = factories.ProfileFactory.create_batch(
            size=2,
            organization_id=self.profile.organization_id,
            team_id=self.profile.team_id,
        )
        with self.mock_transport() as mock:
            mock.instance.register_mock_object(
                service='organization',
                action='get_team',
                return_object_path='team',
                return_object=team,
                mock_regex_lookup='organization:get_team:.*',
            )
            response = self.client.call_action('get_peers', profile_id=self.profile.id)
        self.assertTrue(response.success)
        self.assertEqual(len(response.result.profiles), len(peers))

    def test_get_peers(self):
        manager = factories.ProfileFactory.create_protobuf(
            organization_id=self.profile.organization_id,
        )
        parent_team = mocks.mock_team(
            id=manager.team_id,
            owner_id=manager.user_id,
            organization_id=self.profile.organization_id,
        )

        team = mocks.mock_team(
            id=self.profile.team_id,
            owner_id=self.profile.user_id,
            path=list(parent_team.path),
            organization_id=self.profile.organization_id,
        )
        teams = [team]
        for _ in range(2):
            profile = factories.ProfileFactory.create_protobuf(
                organization_id=self.profile.organization_id,
            )
            teams.append(
                mocks.mock_team(
                    path=list(parent_team.path),
                    id=profile.team_id,
                    owner_id=profile.user_id,
                )
            )

        with self.mock_transport() as mock:
            mock.instance.dont_mock_service('profile')
            mock.instance.register_mock_object(
                service='organization',
                action='get_team',
                return_object_path='team',
                return_object=team,
                team_id=str(uuid.UUID(team.id)),
            )
            mock.instance.register_mock_object(
                service='organization',
                action='get_team',
                return_object_path='team',
                return_object=parent_team,
                team_id=str(uuid.UUID(parent_team.id)),
            )
            mock.instance.register_mock_object(
                service='organization',
                action='get_team_descendants',
                return_object_path='descendants',
                return_object=[mocks.mock_team_descendants(teams=teams)],
                mock_regex_lookup='organization:get_team_descendants:.*',
            )
            response = self.client.call_action('get_peers', profile_id=self.profile.id)
        self.assertTrue(response.success)
        self.assertEqual(len(response.result.profiles), 2)

        # verify peers are sorted alphabetically by first_name, last_name
        sorted_profiles = sorted(
            response.result.profiles,
            key=lambda x: (x.first_name.lower(), x.last_name.lower()),
        )
        for index, profile in enumerate(response.result.profiles):
            self.verify_containers(sorted_profiles[index], profile)

    def test_get_peers_ceo(self):
        team = mocks.mock_team(
            id=self.profile.team_id,
            organization_id=self.profile.organization_id,
            owner_id=self.profile.user_id,
        )

        with self.mock_transport() as mock:
            mock.instance.register_mock_object(
                service='organization',
                action='get_team',
                return_object_path='team',
                return_object=team,
                mock_regex_lookup='organization:get_team:.*',
            )
            response = self.client.call_action('get_peers', profile_id=self.profile.id)
        self.assertTrue(response.success)
        self.assertEqual(len(response.result.profiles), 0)

    def test_get_peers_ceo_members_on_direct_team(self):
        team = mocks.mock_team(
            id=self.profile.team_id,
            organization_id=self.profile.organization_id,
            owner_id=self.profile.user_id,
        )
        # add someone on his direct team (C level exec)
        factories.ProfileFactory.create(
            organization_id=self.profile.organization_id,
            team_id=team.id,
        )

        with self.mock_transport() as mock:
            mock.instance.register_mock_object(
                service='organization',
                action='get_team',
                return_object_path='team',
                return_object=team,
                mock_regex_lookup='organization:get_team:.*',
            )
            response = self.client.call_action('get_peers', profile_id=self.profile.id)
        self.assertEqual(len(response.result.profiles), 0)

    def test_get_profile_stats_address_invalid(self):
        with self.assertFieldError('address_ids'):
            self.client.call_action('get_profile_stats', address_ids=['invalid'])

    def test_get_profile_stats_address_no_profiles(self):
        response = self.client.call_action(
            'get_profile_stats',
            address_ids=[fuzzy.FuzzyUUID().fuzz()],
        )
        self.assertTrue(response.success)
        stats = response.result.stats[0]
        self.assertEqual(stats.count, 0)

    def test_get_profile_stats_address(self):
        address_id = fuzzy.FuzzyUUID().fuzz()
        factories.ProfileFactory.create_batch(5, address_id=address_id)
        response = self.client.call_action('get_profile_stats', address_ids=[address_id])
        self.assertTrue(response.success)
        stats = response.result.stats[0]
        self.assertEqual(stats.count, 5)

    def test_get_profile_stats_team_invalid(self):
        with self.assertFieldError('team_ids'):
            self.client.call_action('get_profile_stats', team_ids=['invalid'])

    def test_get_profile_stats_team_no_profiles(self):
        team_id = fuzzy.FuzzyUUID().fuzz()
        with self.mock_transport(self.client) as mock:
            self._mock_get_team_descendants(mock, team_id, [])
            response = self.client.call_action(
                'get_profile_stats',
                team_ids=[team_id],
            )
        self.assertEqual(response.result.stats[0].count, 0)

    def test_get_profile_stats_team_ids(self):
        team_id = fuzzy.FuzzyUUID().fuzz()
        sub_team_ids = [fuzzy.FuzzyUUID().fuzz(), fuzzy.FuzzyUUID().fuzz()]
        factories.ProfileFactory.create_batch(5, team_id=team_id)
        for sub_team_id in sub_team_ids:
            factories.ProfileFactory.create(team_id=sub_team_id)

        with self.mock_transport(self.client) as mock:
            self._mock_get_team_descendants(mock, team_id, sub_team_ids)
            response = self.client.call_action('get_profile_stats', team_ids=[team_id])
        self.assertEqual(response.result.stats[0].count, 7)

    def test_get_profile_stats_location_invalid(self):
        with self.assertFieldError('location_ids'):
            self.client.call_action('get_profile_stats', location_ids=['invalid'])

    def test_get_profile_stats_location_no_profiles(self):
        response = self.client.call_action(
            'get_profile_stats',
            location_ids=[fuzzy.FuzzyUUID().fuzz()],
        )
        self.assertTrue(response.success)
        stats = response.result.stats[0]
        self.assertEqual(stats.count, 0)

    def test_get_profile_stats_location(self):
        location_id = fuzzy.FuzzyUUID().fuzz()
        factories.ProfileFactory.create_batch(5, location_id=location_id)
        response = self.client.call_action('get_profile_stats', location_ids=[location_id])
        self.assertTrue(response.success)
        stats = response.result.stats[0]
        self.assertEqual(stats.count, 5)

    def test_create_profile_duplicate(self):
        profile = factories.ProfileFactory.create_protobuf()
        with self.assertRaisesCallActionError() as expected:
            self.client.call_action('create_profile', profile=profile)
        self.assertIn('DUPLICATE', expected.exception.response.errors)

    def test_get_upcoming_anniversaries_invalid_organization_id(self):
        with self.assertFieldError('organization_id'):
            self.client.call_action('get_upcoming_anniversaries', organization_id='invalid')

    def test_get_upcoming_anniversaries_organization_id_required(self):
        with self.assertFieldError('organization_id', 'MISSING'):
            self.client.call_action('get_upcoming_anniversaries')

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
        with self.assertFieldError('organization_id'):
            self.client.call_action('get_upcoming_birthdays', organization_id='invalid')

    def test_get_upcoming_birthdays_organization_id_required(self):
        with self.assertFieldError('organization_id', 'MISSING'):
            self.client.call_action('get_upcoming_birthdays')

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
        with self.assertFieldError('organization_id'):
            self.client.call_action('get_recent_hires', organization_id='invalid')

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
        with self.assertFieldError('organization_id'):
            self.client.call_action(
                'get_active_tags',
                organization_id='invalid',
                tag_type=profile_containers.TagV1.SKILL,
            )

    def test_get_active_tags(self):
        organization_id = fuzzy.FuzzyUUID().fuzz()
        skills = factories.TagFactory.create_batch(
            size=3,
            organization_id=organization_id,
            type=profile_containers.TagV1.SKILL,
        )
        # create interests that SHOULD be included
        interests = factories.TagFactory.create_batch(
            size=3,
            organization_id=organization_id,
            type=profile_containers.TagV1.INTEREST,
        )
        profile = factories.ProfileFactory.create(
            tags=[skills[1], interests[1]],
            organization_id=organization_id,
        )
        # create a profile in another organization
        factories.ProfileFactory.create(tags=[factories.TagFactory.create()])
        # add duplicate
        factories.ProfileFactory.create(tags=[skills[1]])
        response = self.client.call_action(
            'get_active_tags',
            organization_id=str(profile.organization_id),
        )
        self.assertTrue(response.success)
        # since we didn't specify tag_type we should get back all active tags
        # for the organization
        self.assertEqual(len(response.result.tags), 2)

    def test_get_active_tags_skills(self):
        organization_id = fuzzy.FuzzyUUID().fuzz()
        skills = factories.TagFactory.create_batch(
            size=3,
            organization_id=organization_id,
            type=profile_containers.TagV1.SKILL,
        )
        # create interests that shouldn't be included
        interests = factories.TagFactory.create_batch(
            size=3,
            organization_id=organization_id,
            type=profile_containers.TagV1.INTEREST,
        )
        profile = factories.ProfileFactory.create(
            tags=[skills[1], interests[1]],
            organization_id=organization_id,
        )
        # create a profile in another organization
        factories.ProfileFactory.create(tags=[factories.TagFactory.create()])
        # add duplicate
        factories.ProfileFactory.create(tags=[skills[1]])
        response = self.client.call_action(
            'get_active_tags',
            organization_id=str(profile.organization_id),
            tag_type=profile_containers.TagV1.SKILL,
        )
        self.assertTrue(response.success)
        self.assertEqual(len(response.result.tags), 1)

    def test_get_profiles_address_id_invalid(self):
        with self.assertFieldError('address_id'):
            self.client.call_action('get_profiles', address_id='invalid')

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
        with self.assertFieldError('ids'):
            self.client.call_action('get_profiles', ids=['invalid'])

    def test_get_profiles_with_id_list(self):
        profiles = factories.ProfileFactory.create_batch(size=5)
        response = self.client.call_action(
            'get_profiles',
            ids=[str(profile.id) for profile in profiles],
        )
        self.assertTrue(response.success)
        self.assertEqual(len(response.result.profiles), 5)

    def test_bulk_create_profiles(self):
        profiles = []
        for _ in range(3):
            profiles.append(mocks.mock_profile())

        response = self.client.call_action('bulk_create_profiles', profiles=profiles)
        self.assertEqual(len(response.result.profiles), len(profiles))

    def test_get_profiles_with_location_id(self):
        location_id = fuzzy.FuzzyUUID().fuzz()
        organization_id = fuzzy.FuzzyUUID().fuzz()
        profiles = factories.ProfileFactory.create_batch(
            size=5,
            location_id=location_id,
            organization_id=organization_id,
        )
        factories.ProfileFactory.create_batch(size=5, organization_id=organization_id)
        response = self.client.call_action('get_profiles', location_id=location_id)
        self.assertEqual(len(profiles), len(response.result.profiles))

    def test_get_profiles_with_emails(self):
        organization_id = fuzzy.FuzzyUUID().fuzz()
        profiles = factories.ProfileFactory.create_batch(
            size=3,
            organization_id=organization_id,
        )
        factories.ProfileFactory.create_batch(size=2, organization_id=organization_id)
        response = self.client.call_action('get_profiles', emails=[x.email for x in profiles])
        self.assertEqual(len(profiles), len(response.result.profiles))

    def test_get_profiles_with_location_id_invalid_location_id(self):
        with self.assertFieldError('location_id'):
            self.client.call_action('get_profiles', location_id='invalid')

    def test_get_attributes_for_profiles_with_invalid_location_id(self):
        with self.assertFieldError('location_id'):
            self.client.call_action(
                'get_attributes_for_profiles',
                location_id='invalid',
                attributes=['team_id'],
            )

    def test_get_attributes_for_profiles_location_id_required(self):
        with self.assertFieldError('location_id', 'MISSING'):
            self.client.call_action(
                'get_attributes_for_profiles',
                attributes=['team_id'],
            )

    def test_get_attributes_for_profiles_attributes_required(self):
        with self.assertFieldError('attributes', 'MISSING'):
            self.client.call_action(
                'get_attributes_for_profiles',
                location_id=fuzzy.FuzzyUUID().fuzz(),
            )

    def test_get_attributes_for_profiles_team_id_by_location_id_distinct(self):
        location_id = fuzzy.FuzzyUUID().fuzz()
        team_id = fuzzy.FuzzyUUID().fuzz()
        factories.ProfileFactory.create_batch(
            size=2,
            location_id=location_id,
            team_id=team_id,
        )
        factories.ProfileFactory.create_batch(3, location_id=location_id)

        response = self.client.call_action(
            'get_attributes_for_profiles',
            location_id=location_id,
            attributes=['team_id'],
            distinct=True,
        )
        self.assertEqual(len(response.result.attributes), 4)

    def test_get_attributes_for_profiles_non_distinct(self):
        location_id = fuzzy.FuzzyUUID().fuzz()
        team_id = fuzzy.FuzzyUUID().fuzz()
        factories.ProfileFactory.create_batch(4, location_id=location_id, team_id=team_id)
        response = self.client.call_action(
            'get_attributes_for_profiles',
            location_id=location_id,
            attributes=['team_id'],
        )
        self.assertEqual(len(response.result.attributes), 4)

    def test_get_attributes_for_profiles_invalid_attribute_by_location_id(self):
        location_id = fuzzy.FuzzyUUID().fuzz()
        factories.ProfileFactory.create(location_id=location_id)
        with self.assertFieldError('attributes'):
            self.client.call_action(
                'get_attributes_for_profiles',
                attributes=['invalid'],
                location_id=location_id,
            )
