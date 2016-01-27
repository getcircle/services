import uuid

import arrow
import mock
from protobufs.services.profile import containers_pb2 as profile_containers

from services.test import (
    fuzzy,
    mocks,
    MockedTestCase,
)

from profiles.factories import ProfileFactory
from profiles.models import Profile
from profiles.sync.providers.okta import (
    _create_profile,
    _get_profile_from_user,
    _get_profiles,
    _sync_profile,
    _sync_users,
    FieldValueInvalidTypeError,
    InvalidFieldTypeError,
    ProviderMappings,
    RequiredFieldMissingError,
)


class Test(MockedTestCase):

    def setUp(self):
        super(Test, self).setUp()
        self.rules = {
            'validate_fields': {
                'profile.employeeNumber': {
                    'required': True,
                    'type': 'str',
                },
                'profile.locale': {
                    'required': True,
                    'type': 'str',
                    'values': ['TSF', 'TSL'],
                },
                'profile.email': {
                    'required': True,
                    'type': 'str',
                },
                'profile.firstName': {
                    'required': True,
                    'type': 'str',
                },
                'profile.lastName': {
                    'required': True,
                    'type': 'str',
                },
                'created': {
                    'type': '_date',
                },
                'profile.managerId': {
                    'type': 'str',
                },
            },
            'mappings': ProviderMappings(**{
                'authentication_identifier': 'profile.employeeNumber',
                'title': 'profile.title',
                'first_name': 'profile.firstName',
                'last_name': 'profile.lastName',
                'hire_date': 'created',
                'email': 'profile.email',
                'manager_authentication_identifier': 'profile.managerId',
                'source_id': 'id',
            }),
        }

    def _provider_user_factory(self, profile_overrides=None, **overrides):
        profile_overrides = profile_overrides or {}
        user = {
            'id': fuzzy.uuid(),
            'profile': {
                'title': fuzzy.text(),
                'employeeNumber': fuzzy.uuid(),
                'email': fuzzy.email(),
                'firstName': fuzzy.text(),
                'lastName': fuzzy.text(),
            },
            'created': '2015-07-01T18:49:15.000Z',
        }
        user['profile'].update(profile_overrides)
        user.update(overrides)
        return user

    def test_get_profile_from_user(self):
        user = self._provider_user_factory()
        rules = {
            'validate_fields': {
                'created': {
                    'type': '_date',
                },
            },
            'mappings': ProviderMappings(
                authentication_identifier='profile.employeeNumber',
                title='profile.title',
                source_id='id',
                hire_date='created',
            ),
        }
        profile = _get_profile_from_user(user, rules)
        self.assertEqual(profile['authentication_identifier'], user['profile']['employeeNumber'])
        self.assertEqual(profile['title'], user['profile']['title'])
        self.assertEqual(profile['source_id'], user['id'])
        self.assertEqual(profile['hire_date'], arrow.get(user['created']).format('YYYY-MM-DD'))

    def test_get_profile_from_user_validate_fields_filter(self):
        user = self._provider_user_factory(
            profile_overrides={
                'title': 'invalid',
                'locale': 'TSP',
            },
        )
        users = [user]
        for i in range(4):
            if i % 2:
                locale = 'TSF'
            else:
                locale = 'TSL'
            overrides = {
                'locale': locale,
                'title': 'valid',
            }
            users.append(self._provider_user_factory(profile_overrides=overrides))

        rules = {
            'validate_fields': {
                'profile.locale': {
                    'required': True,
                    'type': 'str',
                    'values': ['TSF', 'TSL'],
                },
            },
            'mappings': ProviderMappings(
                title='profile.title',
            ),
        }
        profiles = _get_profiles(users, rules)
        self.assertEqual(len(profiles), 4)
        for profile in profiles:
            self.assertEqual(profile['title'], 'valid')

    def test_get_profile_from_user_validate_fields_unwhite_listed_field_type(self):
        user = self._provider_user_factory({'locale': 'a'})
        rules = {
            'validate_fields': {
                'profile.locale': {
                    'required': True,
                    'type': 'invalid',
                },
            },
            'mappings': ProviderMappings(
                title='profile.title',
            ),
        }
        with self.assertRaises(InvalidFieldTypeError):
            _get_profile_from_user(user, rules)

    def test_get_profile_from_user_validate_fields_invalid_field_type(self):
        user = self._provider_user_factory({'locale': 'a'})
        rules = {
            'validate_fields': {
                'profile.locale': {
                    'required': True,
                    'type': 'int',
                },
            },
            'mappings': ProviderMappings(
                title='profile.title',
            ),
        }
        with self.assertRaises(FieldValueInvalidTypeError):
            _get_profile_from_user(user, rules)

    def test_get_profile_from_user_validate_fields_missing_required_field(self):
        user = self._provider_user_factory()
        rules = {
            'validate_fields': {
                'profile.locale': {
                    'required': True,
                    'type': 'str',
                },
            },
            'mappings': ProviderMappings(
                title='profile.title',
            ),
        }
        with self.assertRaises(RequiredFieldMissingError):
            _get_profile_from_user(user, rules)

    def test_create_profile(self):
        provider_profile = {
            'title': fuzzy.text(),
            'first_name': fuzzy.text(),
            'last_name': fuzzy.text(),
            'hire_date': '2015-07-01',
            'email': fuzzy.FuzzyText(suffix='@example.com').fuzz(),
            'manager_lookup': fuzzy.uuid(),
            'source_id': fuzzy.uuid(),
            'authentication_identifier': fuzzy.uuid(),
        }
        organization_id = fuzzy.uuid()
        user = mocks.mock_user(
            primary_email=provider_profile['email'],
            organization_id=organization_id,
        )
        self.mock.instance.register_mock_object(
            service='user',
            action='create_user',
            return_object_path='user',
            return_object=user,
            email=provider_profile['email'],
            organization_id=organization_id,
        )
        profile = _create_profile(provider_profile, organization_id)
        self.assertEqual(profile.title, provider_profile['title'])
        self.assertEqual(profile.first_name, provider_profile['first_name'])
        self.assertEqual(profile.last_name, provider_profile['last_name'])
        self.assertEqual(profile.sync_source_id, provider_profile['source_id'])
        self.assertEqual(profile.hire_date, arrow.get('2015-07-01').date())

    def test_create_profile_empty_title_empty_hire_date(self):
        provider_profile = {
            'first_name': fuzzy.text(),
            'last_name': fuzzy.text(),
            'email': fuzzy.FuzzyText(suffix='@example.com').fuzz(),
            'manager_lookup': fuzzy.uuid(),
            'source_id': fuzzy.uuid(),
            'authentication_identifier': fuzzy.uuid(),
        }
        organization_id = fuzzy.uuid()
        user = mocks.mock_user(
            primary_email=provider_profile['email'],
            organization_id=organization_id,
        )
        self.mock.instance.register_mock_object(
            service='user',
            action='create_user',
            return_object_path='user',
            return_object=user,
            email=provider_profile['email'],
            organization_id=organization_id,
        )
        profile = _create_profile(provider_profile, organization_id)
        self.assertIsNone(profile.title)
        self.assertIsNone(profile.hire_date)

    def test_sync_profile(self):
        provider_profile = {
            'title': fuzzy.text(),
            'first_name': fuzzy.text(),
            'last_name': fuzzy.text(),
            'hire_date': '2015-07-01',
            'email': fuzzy.FuzzyText(suffix='@example.com').fuzz(),
            'manager_lookup': fuzzy.uuid(),
            'source_id': fuzzy.uuid(),
            'authentication_identifier': fuzzy.uuid(),
        }
        old_profile = ProfileFactory.create()
        profile = _sync_profile(provider_profile, old_profile)
        self.assertEqual(profile.first_name, provider_profile['first_name'])
        self.assertEqual(profile.last_name, provider_profile['last_name'])
        self.assertEqual(profile.email, provider_profile['email'])
        self.assertEqual(profile.sync_source_id, provider_profile['source_id'])
        self.assertEqual(
            profile.authentication_identifier,
            provider_profile['authentication_identifier'],
        )
        self.assertEqual(profile.id, old_profile.id)
        self.assertEqual(profile.hire_date, arrow.get('2015-07-01').date())

    def test_sync_profile_empty_title_empty_hire_date(self):
        provider_profile = {
            'first_name': fuzzy.text(),
            'last_name': fuzzy.text(),
            'email': fuzzy.FuzzyText(suffix='@example.com').fuzz(),
            'manager_lookup': fuzzy.uuid(),
            'source_id': fuzzy.uuid(),
            'authentication_identifier': fuzzy.uuid(),
        }
        old_profile = ProfileFactory.create()
        profile = _sync_profile(provider_profile, old_profile)
        self.assertEqual(profile.first_name, provider_profile['first_name'])
        self.assertEqual(profile.last_name, provider_profile['last_name'])
        self.assertEqual(profile.email, provider_profile['email'])
        self.assertEqual(profile.sync_source_id, provider_profile['source_id'])
        self.assertEqual(
            profile.authentication_identifier,
            provider_profile['authentication_identifier'],
        )
        self.assertEqual(profile.id, old_profile.id)

    @mock.patch('profiles.sync.providers.okta._set_manager')
    def test_sync_users(self, mocked_set_manager):
        organization_id = fuzzy.uuid()
        ProfileFactory.create(organization_id=organization_id)

        factory_args = [
            {'locale': 'TSF', 'employeeNumber': 1},
            {'locale': 'TSF', 'managerId': 1, 'employeeNumber': 2},
            {'locale': 'TSL', 'managerId': 2},
            {'locale': 'TSL', 'managerId': 2},
        ]
        users = [self._provider_user_factory(args) for args in factory_args]

        for user in users:
            self.mock.instance.register_mock_object(
                service='user',
                action='create_user',
                return_object_path='user',
                return_object=mocks.mock_user(organization_id=organization_id),
                organization_id=organization_id,
                email=user['profile']['email'],
            )

        _sync_users(users, self.rules, organization_id)
        active_profiles = Profile.objects.filter(
            organization_id=organization_id,
            status=profile_containers.ProfileV1.ACTIVE,
        )
        inactive_profiles = Profile.objects.filter(
            organization_id=organization_id,
            status=profile_containers.ProfileV1.INACTIVE,
        )
        self.assertEqual(len(active_profiles), 4)
        self.assertEqual(len(inactive_profiles), 1)
        self.assertEqual(mocked_set_manager.call_count, 3)
        for call in mocked_set_manager.call_args_list:
            for arg in call[0][:2]:
                try:
                    valid = bool(uuid.UUID(arg))
                except ValueError:
                    valid = False
                self.assertTrue(valid, 'first two args should be UUID: %s' % (arg,))
