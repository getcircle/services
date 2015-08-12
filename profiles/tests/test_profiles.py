import datetime

from freezegun import freeze_time
from protobufs.services.profile import containers_pb2 as profile_containers
import service.control

from services.test import (
    fuzzy,
    mocks,
    MockedTestCase,
)

from .. import (
    factories,
    models,
)


class TestProfiles(MockedTestCase):

    def setUp(self):
        super(TestProfiles, self).setUp()
        self.organization = mocks.mock_organization()
        self.profile = factories.ProfileFactory.create_protobuf(
            organization_id=self.organization.id,
        )
        token = mocks.mock_token(
            profile_id=self.profile.id,
            organization_id=self.organization.id,
        )
        self.client = service.control.Client('profile', token=token)
        self.mock.instance.dont_mock_service('profile')

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

    def test_get_profile(self):
        status = profile_containers.ProfileStatusV1(value='some status')
        expected = factories.ProfileFactory.create_protobuf(
            status=status,
            organization_id=self.organization.id,
        )
        response = self.client.call_action(
            'get_profile',
            profile_id=expected.id,
        )
        self.verify_containers(expected, response.result.profile)
        self.verify_containers(status, response.result.profile.status)

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
        original = factories.ProfileFactory.create_protobuf(status={'value': 'old status'})
        profile = profile_containers.ProfileV1()
        profile.CopyFrom(original)

        profile.first_name = 'Michael'
        profile.last_name = 'Hahn'
        profile.title = 'Engineer'

        new_status = 'new status'
        profile.status.CopyFrom(profile_containers.ProfileStatusV1(value=new_status))

        # this has no effect, this just makes validating the container easier
        profile.full_name = 'Michael Hahn'

        response = self.client.call_action('update_profile', profile=profile)
        self.verify_containers(profile, response.result.profile, ignore_fields='status')
        self.assertEqual(new_status, response.result.profile.status.value)
        self.assertTrue(response.result.profile.status.created)
        self.assertTrue(models.ProfileStatus.objects.filter(profile_id=profile.id).count(), 2)

    def test_update_profile_status_didnt_change(self):
        original = factories.ProfileFactory.create_protobuf(
            status={'value': 'old status'},
            organization_id=self.organization.id,
        )
        profile = profile_containers.ProfileV1.FromString(original.SerializeToString())
        profile.first_name = 'Michael'
        self.client.call_action('update_profile', profile=profile)
        response = self.client.call_action('get_profile', profile_id=profile.id)
        self.verify_containers(response.result.profile.status, profile.status)

    def test_update_profile_unset_status(self):
        original = factories.ProfileFactory.create_protobuf(
            status={'value': 'old status'},
            organization_id=self.organization.id,
        )
        profile = profile_containers.ProfileV1.FromString(original.SerializeToString())
        profile.ClearField('status')
        self.client.call_action('update_profile', profile=profile)
        response = self.client.call_action('get_profile', profile_id=profile.id)
        self.assertFalse(response.result.profile.HasField('status'))

        response = self.client.call_action('update_profile', profile=profile)
        self.assertFalse(response.result.profile.HasField('status'))
        self.assertEqual(models.ProfileStatus.objects.filter(profile_id=profile.id).count(), 2)

    def test_update_profile_get_profile_only_returns_most_recent_status(self):
        original = factories.ProfileFactory.create_protobuf(
            status={'value': 'old status'},
            organization_id=self.organization.id,
        )
        profile = profile_containers.ProfileV1.FromString(original.SerializeToString())
        new_status = 'new status'
        profile.status.CopyFrom(profile_containers.ProfileStatusV1(value=new_status))

        self.client.call_action('update_profile', profile=profile)
        response = self.client.call_action('get_profile', profile_id=profile.id)
        self.assertEqual(response.result.profile.status.value, new_status)

    def test_update_profile_no_previous_status(self):
        original = factories.ProfileFactory.create_protobuf()
        profile = profile_containers.ProfileV1.FromString(original.SerializeToString())
        new_status = 'new status'
        profile.status.CopyFrom(profile_containers.ProfileStatusV1(value=new_status))

        response = self.client.call_action('update_profile', profile=profile)
        self.assertEqual(response.result.profile.status.value, new_status)

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

    def test_bulk_create_profiles(self):
        profiles = []
        for _ in range(3):
            profiles.append(mocks.mock_profile())

        response = self.client.call_action('bulk_create_profiles', profiles=profiles)
        self.assertEqual(len(response.result.profiles), len(profiles))

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

    def test_get_profiles_invalid_id_list(self):
        with self.assertFieldError('ids'):
            self.client.call_action('get_profiles', ids=['invalid'])

    def test_get_profiles_with_id_list(self):
        profiles = factories.ProfileFactory.create_batch(
            size=5,
            organization_id=self.organization.id,
        )
        response = self.client.call_action(
            'get_profiles',
            ids=[str(profile.id) for profile in profiles],
        )
        self.assertTrue(response.success)
        self.assertEqual(len(response.result.profiles), 5)

    def test_get_profiles_with_location_id(self):
        profiles = factories.ProfileFactory.create_batch(
            size=5,
            organization_id=self.organization.id,
        )
        location_id = fuzzy.FuzzyUUID().fuzz()
        self.mock.instance.register_mock_object(
            'organization',
            'get_location_members',
            return_object_path='member_profile_ids',
            return_object=[str(profile.id) for profile in profiles[:3]],
            location_id=location_id,
        )
        response = self.client.call_action('get_profiles', location_id=location_id)
        self.assertEqual(len(response.result.profiles), 3)

    def test_get_profiles_with_location_id_invalid_location_id(self):
        with self.assertFieldError('location_id'):
            self.client.call_action('get_profiles', location_id='invalid')
