import contextlib
from functools import partial
from mock import (
    MagicMock,
    patch,
)
from pprint import pprint

from apiclient.errors import HttpError
from protobufs.services.group import containers_pb2 as group_containers

from services.test import TestCase
from services.test import (
    fuzzy,
    mocks,
)

from .. import factories
from ..providers import exceptions
from ..providers.google import Provider


class BaseGoogleCase(TestCase):

    def setUp(self):
        super(BaseGoogleCase, self).setUp()
        self.organization = mocks.mock_organization(domain='circlehq.co')
        self.for_profile = mocks.mock_profile(
            email='michael@circlehq.co',
            organization_id=self.organization.id,
        )
        self.by_profile = mocks.mock_profile(
            email='ravi@circlehq.co',
            organization_id=self.organization.id,
        )
        token = mocks.mock_token(
            organization_id=self.organization.id,
            profile_id=self.by_profile.id,
        )
        self.provider = Provider(self.by_profile, self.organization, token=token)

    def _structure_fixtures(self, groups, membership=None, members=None, managers=None):
        if membership is None:
            membership = {}

        if members is None:
            members = tuple()

        if managers is None:
            managers = tuple()

        return {
            'groups': factories.GoogleProviderGroupsFactory(groups).as_dict(),
            'settings': dict((x.email, x.settings.as_dict()) for x in groups),
            'membership': membership,
            'members': members,
            'managers': managers,
        }

    def _parse_test_case(self, raw):
        test_case = {}
        for key, value in raw.iteritems():
            previous_part = test_case
            parts = key.split(':')
            for index, part in enumerate(parts):
                if index == len(parts) - 1:
                    previous_part[part] = value
                else:
                    previous_part = previous_part.setdefault(part, {})

        if 'provider_func_args' in test_case:
            for key in test_case['provider_func_args'].keys():
                value = test_case['provider_func_args'].pop(key)
                if isinstance(value, basestring) and ':' in value:
                    value_parts = value.split(':')
                    previous_part = test_case
                    for index, part in enumerate(value_parts):
                        if index == len(value_parts) - 1:
                            test_case['provider_func_args'][int(key)] = previous_part[part]
                        else:
                            previous_part = previous_part[part]
                else:
                    test_case['provider_func_args'][int(key)] = value
        return test_case

    def _execute_test_cases(
            self,
            provider_func_name,
            test_cases,
            provider_func_args=None,
            test_func=None,
        ):
        # TODO switch to generator test case
        for test_case in test_cases:
            test_case = self._parse_test_case(test_case)
            setup = test_case.get('setup', {})
            settings = setup.get('settings', {})
            membership = setup.get('membership', {})
            members = setup.get('members', [])
            managers = setup.get('managers', [])
            func_args = None
            if provider_func_args is None and 'provider_func_args' in test_case:
                func_args = test_case['provider_func_args']
                func_args = [x[1] for x in sorted(
                    func_args.items(),
                    key=lambda x: x[0],
                )]

            group_kwargs = {}
            for key, value in setup.get('group', {}).iteritems():
                group_kwargs[key] = value
            for key, value in settings.iteritems():
                group_kwargs['settings__%s' % (key,)] = value

            group = factories.GoogleGroupFactory(**group_kwargs)
            if membership:
                membership = {group.email: factories.GoogleGroupMember(**membership).as_dict()}

            fixtures = self._structure_fixtures(
                [group],
                membership=membership,
                members=members,
                managers=managers,
            )
            try:
                self._execute_test(
                    provider_func_name,
                    test_case.get('assertions'),
                    fixtures,
                    provider_func_args=provider_func_args or func_args,
                    test_func=test_func,
                )
            except AssertionError:
                print '\nTest Case Failed:'
                pprint(test_case)
                raise


class TestGoogleListGroups(BaseGoogleCase):

    def _execute_test(
            self,
            provider_func_name,
            assertions,
            fixtures,
            provider_func_args=None,
            test_func=None,
        ):
        if provider_func_args is None:
            provider_func_args = tuple()

        patch_get_managers = patch.object(
            self.provider,
            '_get_group_managers',
            return_value=fixtures['managers'],
        )
        patch_get_group = patch.object(
            self.provider,
            '_get_group',
            return_value=fixtures['groups']['groups'][0],
        )
        patch_get_groups = patch.object(
            self.provider,
            '_get_groups',
            return_value=fixtures['groups'],
        )
        patch_get_group_settings_and_membership = patch.object(
            self.provider,
            '_get_groups_settings_and_membership',
            return_value=(fixtures['settings'], fixtures['membership']),
        )
        with contextlib.nested(
            patch_get_group,
            patch_get_groups,
            patch_get_group_settings_and_membership,
            patch_get_managers
        ):
            partial_method = partial(
                getattr(self.provider, provider_func_name),
                *provider_func_args
            )
            expected_exception = assertions.get('raises') if hasattr(assertions, 'get') else None
            if expected_exception:
                with self.assertRaises(expected_exception):
                    partial_method()
                return
            else:
                result = partial_method()
            if test_func:
                test_func(assertions, result)
            else:
                if callable(assertions):
                    assertions(result)
                else:
                    try:
                        group = result[0]
                    except IndexError:
                        if assertions['group']['can_view']:
                            raise AssertionError('Group should have been visible')
                        return
                    else:
                        if not assertions['group']['can_view']:
                            raise AssertionError('Group should not have been visible')

                    for key, value in assertions['group'].iteritems():
                        if key != 'can_view':
                            self.assertEqual(getattr(group, key), value)

    def test_list_groups_for_organization_cases(self):
        test_cases = [
            {
                'setup:settings:whoCanJoin': 'INVITED_CAN_JOIN',
                'setup:settings:whoCanViewMembership': 'ALL_MANAGERS_CAN_VIEW',
                'setup:settings:showInGroupDirectory': False,
                'assertions:group:can_view': False,
            },
            {
                'setup:settings:whoCanJoin': 'INVITED_CAN_JOIN',
                'setup:settings:whoCanViewMembership': 'ALL_MANAGERS_CAN_VIEW',
                'setup:settings:showInGroupDirectory': True,
                'assertions:group:can_view': True,
            },
        ]
        self._execute_test_cases('list_groups_for_organization', test_cases)

    def test_get_group(self):
        test_cases = [
            {
                'setup:group:email': 'group@circlehq.co',
                'setup:settings:whoCanJoin': 'INVITED_CAN_JOIN',
                'setup:settings:whoCanViewMembership': 'ALL_MANAGERS_CAN_VIEW',
                'setup:settings:showInGroupDirectory': False,
                'provider_func_args:0': 'setup:group:email',
                'assertions:group:can_view': False,
            },
            {
                'setup:group:email': 'group@circlehq.co',
                'setup:settings:whoCanJoin': 'INVITED_CAN_JOIN',
                'setup:settings:whoCanViewMembership': 'ALL_MANAGERS_CAN_VIEW',
                'setup:settings:showInGroupDirectory': True,
                'provider_func_args:0': 'setup:group:email',
                'assertions:group:can_view': True,
            },
        ]

        def test(assertions, result):
            if not assertions['group']['can_view'] and result is not None:
                raise AssertionError('Group should not have been visible')
            elif assertions['group']['can_view'] and result is None:
                raise AssertionError('Group should be visible')

        self._execute_test_cases('get_group', test_cases, test_func=test)

    def test_list_groups_for_user_single_group_cases(self):
        test_cases = [
            {
                'setup:settings:whoCanJoin': 'ALL_IN_DOMAIN_CAN_JOIN',
                'setup:settings:whoCanViewMembership': 'ALL_IN_DOMAIN_CAN_VIEW',
                'assertions:group:can_join': True,
                'assertions:group:is_member': False,
                'assertions:group:can_view': True,
            },
            {
                'setup:settings:whoCanJoin': 'ALL_IN_DOMAIN_CAN_JOIN',
                'setup:settings:whoCanViewMembership': 'ALL_MEMBERS_CAN_VIEW',
                'assertions:group:can_join': True,
                'assertions:group:is_member': False,
                'assertions:group:can_view': False,
            },
            {
                'setup:settings:whoCanJoin': 'ALL_IN_DOMAIN_CAN_JOIN',
                'setup:settings:whoCanViewMembership': 'ALL_MANAGERS_CAN_VIEW',
                'assertions:group:can_join': True,
                'assertions:group:is_member': False,
                'assertions:group:can_view': False,
            },
            {
                'setup:settings:whoCanJoin': 'ANYONE_CAN_JOIN',
                'setup:settings:whoCanViewMembership': 'ALL_IN_DOMAIN_CAN_VIEW',
                'assertions:group:can_join': True,
                'assertions:group:is_member': False,
                'assertions:group:can_view': True,
            },
            {
                'setup:settings:whoCanJoin': 'ANYONE_CAN_JOIN',
                'setup:settings:whoCanViewMembership': 'ALL_MEMBERS_CAN_VIEW',
                'assertions:group:can_join': True,
                'assertions:group:is_member': False,
                'assertions:group:can_view': False,
            },
            {
                'setup:settings:whoCanJoin': 'ANYONE_CAN_JOIN',
                'setup:settings:whoCanViewMembership': 'ALL_MANAGERS_CAN_VIEW',
                'assertions:group:can_join': True,
                'assertions:group:is_member': False,
                'assertions:group:can_view': False,
            },
            {
                'setup:settings:whoCanJoin': 'CAN_REQUEST_TO_JOIN',
                'setup:settings:whoCanViewMembership': 'ALL_IN_DOMAIN_CAN_VIEW',
                'assertions:group:can_join': True,
                'assertions:group:is_member': False,
                'assertions:group:can_view': True,
            },
            {
                'setup:settings:whoCanJoin': 'ANYONE_CAN_JOIN',
                'setup:settings:whoCanViewMembership': 'ALL_MEMBERS_CAN_VIEW',
                'assertions:group:can_join': True,
                'assertions:group:is_member': False,
                'assertions:group:can_view': False,
            },
            {
                'setup:settings:whoCanJoin': 'ANYONE_CAN_JOIN',
                'setup:settings:whoCanViewMembership': 'ALL_MANAGERS_CAN_VIEW',
                'assertions:group:can_join': True,
                'assertions:group:is_member': False,
                'assertions:group:can_view': False,
            },
            {
                'setup:settings:whoCanJoin': 'INVITED_CAN_JOIN',
                'setup:settings:whoCanViewMembership': 'ALL_IN_DOMAIN_CAN_VIEW',
                'assertions:group:can_join': False,
                'assertions:group:is_member': False,
                'assertions:group:can_view': True,
            },
            {
                'setup:settings:whoCanJoin': 'INVITED_CAN_JOIN',
                'setup:settings:whoCanViewMembership': 'ALL_MEMBERS_CAN_VIEW',
                'assertions:group:can_join': False,
                'assertions:group:is_member': False,
                'assertions:group:can_view': False,
            },
            {
                'setup:settings:whoCanJoin': 'INVITED_CAN_JOIN',
                'setup:settings:whoCanViewMembership': 'ALL_MANAGERS_CAN_VIEW',
                'assertions:group:can_join': False,
                'assertions:group:is_member': False,
                'assertions:group:can_view': False,
            },
            {
                'setup:settings:whoCanJoin': 'ALL_IN_DOMAIN_CAN_JOIN',
                'setup:settings:whoCanViewMembership': 'ALL_IN_DOMAIN_CAN_VIEW',
                'setup:membership:role': 'MEMBER',
                'setup:membership:email': self.by_profile.email,
                'assertions:group:can_join': False,
                'assertions:group:is_member': True,
                'assertions:group:can_view': True,
            },
            {
                'setup:settings:whoCanJoin': 'ALL_IN_DOMAIN_CAN_JOIN',
                'setup:settings:whoCanViewMembership': 'ALL_MEMBERS_CAN_VIEW',
                'setup:membership:role': 'MEMBER',
                'setup:membership:email': self.by_profile.email,
                'assertions:group:can_join': False,
                'assertions:group:is_member': True,
                'assertions:group:can_view': True,
            },
            {
                'setup:settings:whoCanJoin': 'ALL_IN_DOMAIN_CAN_JOIN',
                'setup:settings:whoCanViewMembership': 'ALL_MANAGERS_CAN_VIEW',
                'setup:membership:role': 'MEMBER',
                'setup:membership:email': self.by_profile.email,
                'assertions:group:can_join': False,
                'assertions:group:is_member': True,
                'assertions:group:can_view': False,
            },
            {
                'setup:settings:whoCanJoin': 'ANYONE_CAN_JOIN',
                'setup:settings:whoCanViewMembership': 'ALL_IN_DOMAIN_CAN_VIEW',
                'setup:membership:role': 'MEMBER',
                'setup:membership:email': self.by_profile.email,
                'assertions:group:can_join': False,
                'assertions:group:is_member': True,
                'assertions:group:can_view': True,
            },
            {
                'setup:settings:whoCanJoin': 'ANYONE_CAN_JOIN',
                'setup:settings:whoCanViewMembership': 'ALL_MEMBERS_CAN_VIEW',
                'setup:membership:role': 'MEMBER',
                'setup:membership:email': self.by_profile.email,
                'assertions:group:can_join': False,
                'assertions:group:is_member': True,
                'assertions:group:can_view': True,
            },
            {
                'setup:settings:whoCanJoin': 'ANYONE_CAN_JOIN',
                'setup:settings:whoCanViewMembership': 'ALL_MANAGERS_CAN_VIEW',
                'setup:membership:role': 'MEMBER',
                'setup:membership:email': self.by_profile.email,
                'assertions:group:can_join': False,
                'assertions:group:is_member': True,
                'assertions:group:can_view': False,
            },
            {
                'setup:settings:whoCanJoin': 'CAN_REQUEST_TO_JOIN',
                'setup:settings:whoCanViewMembership': 'ALL_IN_DOMAIN_CAN_VIEW',
                'setup:membership:role': 'MEMBER',
                'setup:membership:email': self.by_profile.email,
                'assertions:group:can_join': False,
                'assertions:group:is_member': True,
                'assertions:group:can_view': True,
            },
            {
                'setup:settings:whoCanJoin': 'CAN_REQUEST_TO_JOIN',
                'setup:settings:whoCanViewMembership': 'ALL_MEMBERS_CAN_VIEW',
                'setup:membership:role': 'MEMBER',
                'setup:membership:email': self.by_profile.email,
                'assertions:group:can_join': False,
                'assertions:group:is_member': True,
                'assertions:group:can_view': True,
            },
            {
                'setup:settings:whoCanJoin': 'CAN_REQUEST_TO_JOIN',
                'setup:settings:whoCanViewMembership': 'ALL_MANAGERS_CAN_VIEW',
                'setup:membership:role': 'MEMBER',
                'setup:membership:email': self.by_profile.email,
                'assertions:group:can_join': False,
                'assertions:group:is_member': True,
                'assertions:group:can_view': False,
            },
            {
                'setup:settings:whoCanJoin': 'INVITED_CAN_JOIN',
                'setup:settings:whoCanViewMembership': 'ALL_IN_DOMAIN_CAN_VIEW',
                'setup:membership:role': 'MEMBER',
                'setup:membership:email': self.by_profile.email,
                'assertions:group:can_join': False,
                'assertions:group:is_member': True,
                'assertions:group:can_view': True,
            },
            {
                'setup:settings:whoCanJoin': 'INVITED_CAN_JOIN',
                'setup:settings:whoCanViewMembership': 'ALL_MEMBERS_CAN_VIEW',
                'setup:membership:role': 'MEMBER',
                'setup:membership:email': self.by_profile.email,
                'assertions:group:can_join': False,
                'assertions:group:is_member': True,
                'assertions:group:can_view': True,
            },
            {
                'setup:settings:whoCanJoin': 'INVITED_CAN_JOIN',
                'setup:settings:whoCanViewMembership': 'ALL_MANAGERS_CAN_VIEW',
                'setup:membership:role': 'MEMBER',
                'setup:membership:email': self.by_profile.email,
                'assertions:group:can_join': False,
                'assertions:group:is_member': True,
                'assertions:group:can_view': False,
            },
            {
                'setup:settings:whoCanJoin': 'ALL_IN_DOMAIN_CAN_JOIN',
                'setup:settings:whoCanViewMembership': 'ALL_IN_DOMAIN_CAN_VIEW',
                'setup:membership:role': 'MANAGER',
                'setup:membership:email': self.by_profile.email,
                'assertions:group:can_join': False,
                'assertions:group:is_member': True,
                'assertions:group:can_view': True,
            },
            {
                'setup:settings:whoCanJoin': 'ALL_IN_DOMAIN_CAN_JOIN',
                'setup:settings:whoCanViewMembership': 'ALL_MEMBERS_CAN_VIEW',
                'setup:membership:role': 'MANAGER',
                'setup:membership:email': self.by_profile.email,
                'assertions:group:can_join': False,
                'assertions:group:is_member': True,
                'assertions:group:can_view': True,
            },
            {
                'setup:settings:whoCanJoin': 'ALL_IN_DOMAIN_CAN_JOIN',
                'setup:settings:whoCanViewMembership': 'ALL_MANAGERS_CAN_VIEW',
                'setup:membership:role': 'MANAGER',
                'setup:membership:email': self.by_profile.email,
                'assertions:group:can_join': False,
                'assertions:group:is_member': True,
                'assertions:group:can_view': True,
            },
            {
                'setup:settings:whoCanJoin': 'ANYONE_CAN_JOIN',
                'setup:settings:whoCanViewMembership': 'ALL_IN_DOMAIN_CAN_VIEW',
                'setup:membership:role': 'MANAGER',
                'setup:membership:email': self.by_profile.email,
                'assertions:group:can_join': False,
                'assertions:group:is_member': True,
                'assertions:group:can_view': True,
            },
            {
                'setup:settings:whoCanJoin': 'ANYONE_CAN_JOIN',
                'setup:settings:whoCanViewMembership': 'ALL_MEMBERS_CAN_VIEW',
                'setup:membership:role': 'MANAGER',
                'setup:membership:email': self.by_profile.email,
                'assertions:group:can_join': False,
                'assertions:group:is_member': True,
                'assertions:group:can_view': True,
            },
            {
                'setup:settings:whoCanJoin': 'ANYONE_CAN_JOIN',
                'setup:settings:whoCanViewMembership': 'ALL_MANAGERS_CAN_VIEW',
                'setup:membership:role': 'MANAGER',
                'setup:membership:email': self.by_profile.email,
                'assertions:group:can_join': False,
                'assertions:group:is_member': True,
                'assertions:group:can_view': True,
            },
            {
                'setup:settings:whoCanJoin': 'CAN_REQUEST_TO_JOIN',
                'setup:settings:whoCanViewMembership': 'ALL_IN_DOMAIN_CAN_VIEW',
                'setup:membership:role': 'MANAGER',
                'setup:membership:email': self.by_profile.email,
                'assertions:group:can_join': False,
                'assertions:group:is_member': True,
                'assertions:group:can_view': True,
            },
            {
                'setup:settings:whoCanJoin': 'CAN_REQUEST_TO_JOIN',
                'setup:settings:whoCanViewMembership': 'ALL_MEMBERS_CAN_VIEW',
                'setup:membership:role': 'MANAGER',
                'setup:membership:email': self.by_profile.email,
                'assertions:group:can_join': False,
                'assertions:group:is_member': True,
                'assertions:group:can_view': True,
            },
            {
                'setup:settings:whoCanJoin': 'CAN_REQUEST_TO_JOIN',
                'setup:settings:whoCanViewMembership': 'ALL_MANAGERS_CAN_VIEW',
                'setup:membership:role': 'MANAGER',
                'setup:membership:email': self.by_profile.email,
                'assertions:group:can_join': False,
                'assertions:group:is_member': True,
                'assertions:group:can_view': True,
            },
            {
                'setup:settings:whoCanJoin': 'INVITED_CAN_JOIN',
                'setup:settings:whoCanViewMembership': 'ALL_IN_DOMAIN_CAN_VIEW',
                'setup:membership:role': 'MANAGER',
                'setup:membership:email': self.by_profile.email,
                'assertions:group:can_join': False,
                'assertions:group:is_member': True,
                'assertions:group:can_view': True,
            },
            {
                'setup:settings:whoCanJoin': 'INVITED_CAN_JOIN',
                'setup:settings:whoCanViewMembership': 'ALL_MEMBERS_CAN_VIEW',
                'setup:membership:role': 'MANAGER',
                'setup:membership:email': self.by_profile.email,
                'assertions:group:can_join': False,
                'assertions:group:is_member': True,
                'assertions:group:can_view': True,
            },
            {
                'setup:settings:whoCanJoin': 'INVITED_CAN_JOIN',
                'setup:settings:whoCanViewMembership': 'ALL_MANAGERS_CAN_VIEW',
                'setup:membership:role': 'MANAGER',
                'setup:membership:email': self.by_profile.email,
                'assertions:group:can_join': False,
                'assertions:group:is_member': True,
                'assertions:group:can_view': True,
            },
            {
                'setup:settings:whoCanJoin': 'ALL_IN_DOMAIN_CAN_JOIN',
                'setup:settings:whoCanViewMembership': 'ALL_IN_DOMAIN_CAN_VIEW',
                'setup:membership:role': 'OWNER',
                'setup:membership:email': self.by_profile.email,
                'assertions:group:can_join': False,
                'assertions:group:is_member': True,
                'assertions:group:can_view': True,
            },
            {
                'setup:settings:whoCanJoin': 'ALL_IN_DOMAIN_CAN_JOIN',
                'setup:settings:whoCanViewMembership': 'ALL_MEMBERS_CAN_VIEW',
                'setup:membership:role': 'OWNER',
                'setup:membership:email': self.by_profile.email,
                'assertions:group:can_join': False,
                'assertions:group:is_member': True,
                'assertions:group:can_view': True,
            },
            {
                'setup:settings:whoCanJoin': 'ALL_IN_DOMAIN_CAN_JOIN',
                'setup:settings:whoCanViewMembership': 'ALL_MANAGERS_CAN_VIEW',
                'setup:membership:role': 'OWNER',
                'setup:membership:email': self.by_profile.email,
                'assertions:group:can_join': False,
                'assertions:group:is_member': True,
                'assertions:group:can_view': True,
            },
            {
                'setup:settings:whoCanJoin': 'ANYONE_CAN_JOIN',
                'setup:settings:whoCanViewMembership': 'ALL_IN_DOMAIN_CAN_VIEW',
                'setup:membership:role': 'OWNER',
                'setup:membership:email': self.by_profile.email,
                'assertions:group:can_join': False,
                'assertions:group:is_member': True,
                'assertions:group:can_view': True,
            },
            {
                'setup:settings:whoCanJoin': 'ANYONE_CAN_JOIN',
                'setup:settings:whoCanViewMembership': 'ALL_MEMBERS_CAN_VIEW',
                'setup:membership:role': 'OWNER',
                'setup:membership:email': self.by_profile.email,
                'assertions:group:can_join': False,
                'assertions:group:is_member': True,
                'assertions:group:can_view': True,
            },
            {
                'setup:settings:whoCanJoin': 'ANYONE_CAN_JOIN',
                'setup:settings:whoCanViewMembership': 'ALL_MANAGERS_CAN_VIEW',
                'setup:membership:role': 'OWNER',
                'setup:membership:email': self.by_profile.email,
                'assertions:group:can_join': False,
                'assertions:group:is_member': True,
                'assertions:group:can_view': True,
            },
            {
                'setup:settings:whoCanJoin': 'CAN_REQUEST_TO_JOIN',
                'setup:settings:whoCanViewMembership': 'ALL_IN_DOMAIN_CAN_VIEW',
                'setup:membership:role': 'OWNER',
                'setup:membership:email': self.by_profile.email,
                'assertions:group:can_join': False,
                'assertions:group:is_member': True,
                'assertions:group:can_view': True,
            },
            {
                'setup:settings:whoCanJoin': 'CAN_REQUEST_TO_JOIN',
                'setup:settings:whoCanViewMembership': 'ALL_MEMBERS_CAN_VIEW',
                'setup:membership:role': 'OWNER',
                'setup:membership:email': self.by_profile.email,
                'assertions:group:can_join': False,
                'assertions:group:is_member': True,
                'assertions:group:can_view': True,
            },
            {
                'setup:settings:whoCanJoin': 'CAN_REQUEST_TO_JOIN',
                'setup:settings:whoCanViewMembership': 'ALL_MANAGERS_CAN_VIEW',
                'setup:membership:role': 'OWNER',
                'setup:membership:email': self.by_profile.email,
                'assertions:group:can_join': False,
                'assertions:group:is_member': True,
                'assertions:group:can_view': True,
            },
            {
                'setup:settings:whoCanJoin': 'INVITED_CAN_JOIN',
                'setup:settings:whoCanViewMembership': 'ALL_IN_DOMAIN_CAN_VIEW',
                'setup:membership:role': 'OWNER',
                'setup:membership:email': self.by_profile.email,
                'assertions:group:can_join': False,
                'assertions:group:is_member': True,
                'assertions:group:can_view': True,
            },
            {
                'setup:settings:whoCanJoin': 'INVITED_CAN_JOIN',
                'setup:settings:whoCanViewMembership': 'ALL_MEMBERS_CAN_VIEW',
                'setup:membership:role': 'OWNER',
                'setup:membership:email': self.by_profile.email,
                'assertions:group:can_join': False,
                'assertions:group:is_member': True,
                'assertions:group:can_view': True,
            },
            {
                'setup:settings:whoCanJoin': 'INVITED_CAN_JOIN',
                'setup:settings:whoCanViewMembership': 'ALL_MANAGERS_CAN_VIEW',
                'setup:membership:role': 'OWNER',
                'setup:membership:email': self.by_profile.email,
                'assertions:group:can_join': False,
                'assertions:group:is_member': True,
                'assertions:group:can_view': True,
            },
        ]
        self._execute_test_cases(
            'list_groups_for_profile',
            test_cases,
            provider_func_args=(self.for_profile,),
        )

    def test_list_groups_for_user_one_public_one_members_only(self):
        groups = [
            # create public groups with alphabetical names
            factories.GoogleGroupFactory(
                name='b',
                settings__whoCanJoin='ALL_IN_DOMAIN_CAN_JOIN',
                settings__whoCanViewMembership='ALL_IN_DOMAIN_CAN_VIEW',
            ),
            factories.GoogleGroupFactory(
                name='a',
                settings__whoCanJoin='ALL_IN_DOMAIN_CAN_JOIN',
                settings__whoCanViewMembership='ALL_IN_DOMAIN_CAN_VIEW',
            ),
            # create a members only group
            factories.GoogleGroupFactory(
                settings__whoCanJoin='INVITED_CAN_JOIN',
                settings__whoCanViewMembership='ALL_MEMBERS_CAN_VIEW',
            )
        ]

        def assertions(groups):
            self.assertEqual(len(groups), 2)
            group = groups[0]
            self.assertTrue(group.can_join)
            self.assertFalse(group.is_member)
            self.assertEqual(groups[0].name, 'a')
            self.assertEqual(groups[1].name, 'b')

        self._execute_test(
            'list_groups_for_profile',
            assertions,
            self._structure_fixtures(groups),
            provider_func_args=(self.for_profile,),
        )

    def test_list_groups_for_organization_alphabetical(self):
        groups = [
            # create public groups with alphabetical names
            factories.GoogleGroupFactory(
                name='b',
                settings__whoCanJoin='ALL_IN_DOMAIN_CAN_JOIN',
                settings__whoCanViewMembership='ALL_IN_DOMAIN_CAN_VIEW',
                settings__showInGroupDirectory=True,
            ),
            factories.GoogleGroupFactory(
                name='a',
                settings__whoCanJoin='ALL_IN_DOMAIN_CAN_JOIN',
                settings__whoCanViewMembership='ALL_IN_DOMAIN_CAN_VIEW',
                settings__showInGroupDirectory=True,
            ),
            factories.GoogleGroupFactory(
                name='c',
                settings__whoCanJoin='ALL_IN_DOMAIN_CAN_JOIN',
                settings__whoCanViewMembership='ALL_IN_DOMAIN_CAN_VIEW',
                settings__showInGroupDirectory=False,
            ),
        ]

        def assertions(groups):
            self.assertEqual(len(groups), 2)
            group = groups[0]
            self.assertFalse(group.is_member)
            self.assertEqual(groups[0].name, 'a')
            self.assertEqual(groups[1].name, 'b')

        self._execute_test(
            'list_groups_for_organization',
            assertions,
            self._structure_fixtures(groups),
        )

    def test_join_group(self):
        test_cases = [
            {
                'setup:group:email': 'group@circlehq.co',
                'setup:settings:whoCanJoin': 'ANYONE_CAN_JOIN',
                'provider_func_args:0': 'setup:group:email',
                'assertions:request:status': group_containers.APPROVED,
                'assertions:request:meta:whoCanJoin': 'ANYONE_CAN_JOIN',
            },
            {
                'setup:group:email': 'group@circlehq.co',
                'setup:settings:whoCanJoin': 'ALL_IN_DOMAIN_CAN_JOIN',
                'provider_func_args:0': 'setup:group:email',
                'assertions:request:status': group_containers.APPROVED,
                'assertions:request:meta:whoCanJoin': 'ALL_IN_DOMAIN_CAN_JOIN',
            },
            {
                'setup:group:email': 'group@circlehq.co',
                'setup:settings:whoCanJoin': 'INVITED_CAN_JOIN',
                'provider_func_args:0': 'setup:group:email',
                'assertions:request:status': group_containers.DENIED,
                'assertions:request:meta:whoCanJoin': 'INVITED_CAN_JOIN',
            },
            {
                'setup:managers': [
                    factories.GoogleGroupMemberFactory.create(
                        role=group_containers.OWNER,
                    ).as_dict(),
                    factories.GoogleGroupMemberFactory.create(
                        role=group_containers.MANAGER,
                    ).as_dict(),
                ],
                'setup:group:email': 'group@circlehq.co',
                'setup:settings:whoCanJoin': 'CAN_REQUEST_TO_JOIN',
                'provider_func_args:0': 'setup:group:email',
                'assertions:request:status': group_containers.PENDING,
                'assertions:request:meta:whoCanJoin': 'CAN_REQUEST_TO_JOIN',
                'assertions:request:approver_profile_ids': 2,
            },
        ]

        def test(assertions, result):
            self.assertEqual(assertions['request']['status'], result.status)
            self.assertEqual(
                assertions['request']['meta']['whoCanJoin'],
                result.meta['whoCanJoin'],
            )
            expected_approver_ids = assertions['request'].get('approver_profile_ids')
            if expected_approver_ids:
                self.assertEqual(len(result.approver_profile_ids), expected_approver_ids)

        with self.mock_transport() as mock:
            mock.instance.register_mock_object(
                service='profile',
                action='get_profiles',
                return_object_path='profiles',
                return_object=[mocks.mock_profile(), mocks.mock_profile()],
                mock_regex_lookup='.*',
            )
            self._execute_test_cases('join_group', test_cases, test_func=test)

    def test_approve_request_to_join(self):
        managers = [
            factories.GoogleGroupMemberFactory.create(
                email=self.by_profile.email,
                role=group_containers.OWNER,
            ).as_dict(),
            factories.GoogleGroupMemberFactory.create().as_dict(),
        ]
        request = factories.GroupMembershipRequestFactory(
            approver_profile_ids=[self.by_profile.id, fuzzy.FuzzyUUID().fuzz()],
        )
        test_cases = [
            {
                'setup:managers': managers,
                'provider_func_args:0': request,
                'assertions:result:status': group_containers.APPROVED,
            },
            {
                'setup:managers': [factories.GoogleGroupMemberFactory.create().as_dict()],
                'provider_func_args:0': request,
                'assertions:raises': exceptions.Unauthorized,
            }
        ]

        def test(assertions, result):
            self.assertEqual(result.status, group_containers.APPROVED)

        with self.mock_transport() as mock, patch.object(self.provider, '_add_to_group'):
            mock.instance.register_mock_object(
                service='profile',
                action='get_profile',
                return_object_path='profile',
                return_object=mocks.mock_profile(id=request.requester_profile_id),
                mock_regex_lookup='.*',
            )
            self._execute_test_cases('approve_request_to_join', test_cases, test_func=test)


class TestGoogleListMembers(BaseGoogleCase):

    def _execute_test(
            self,
            provider_func_name,
            assertions,
            fixtures,
            provider_func_args=None,
            **kwargs
        ):
        if provider_func_args is None:
            provider_func_args = tuple()

        patched_get_group_members = patch.object(
            self.provider,
            '_get_group_members',
            return_value=fixtures['members'],
        )
        patched_get_groups_settings_and_membership = patch.object(
            self.provider,
            '_get_groups_settings_and_membership',
            return_value=(fixtures['settings'], fixtures['membership']),
        )
        with patched_get_group_members, patched_get_groups_settings_and_membership:
            members = getattr(self.provider, provider_func_name)(*provider_func_args)
            if callable(assertions):
                assertions(members)
            else:
                if isinstance(assertions, dict):
                    for key, value in assertions.iteritems():
                        if key == 'members' and callable(value):
                            value(members)
                        else:
                            raise NotImplemented(
                                'Not sure how to evaluate assertions: %s' % (value,)
                            )
                else:
                    raise NotImplemented('Not sure how to evaluate assertions: %s' % (assertions,))

    def test_list_members(self):
        test_cases = [
            # all in domain can view, not a member
            {
                'setup:group:email': 'group@circlehq.co',
                'setup:settings:whoCanViewMembership': 'ALL_IN_DOMAIN_CAN_VIEW',
                'setup:members': [
                    factories.GoogleGroupMemberFactory.create().as_dict(),
                ],
                'provider_func_args:0': 'setup:group:email',
                'provider_func_args:1': group_containers.MEMBER,
                'assertions:members': lambda x: self.assertEqual(len(x), 1),
            },
            # members only can view, not a member
            {
                'setup:group:email': 'group@circlehq.co',
                'setup:settings:whoCanViewMembership': 'ALL_MEMBERS_CAN_VIEW',
                'setup:members': [
                    factories.GoogleGroupMemberFactory.create().as_dict(),
                ],
                'provider_func_args:0': 'setup:group:email',
                'provider_func_args:1': group_containers.MEMBER,
                'assertions:members': lambda x: self.assertEqual(len(x), 0),
            },
            # managers only can view, not a member
            {
                'setup:group:email': 'group@circlehq.co',
                'setup:settings:whoCanViewMembership': 'ALL_MANAGERS_CAN_VIEW',
                'setup:members': [
                    factories.GoogleGroupMemberFactory.create().as_dict(),
                ],
                'provider_func_args:0': 'setup:group:email',
                'provider_func_args:1': group_containers.MEMBER,
                'assertions:members': lambda x: self.assertEqual(len(x), 0),
            },
            # all in domain can view, a member
            {
                'setup:group:email': 'group@circlehq.co',
                'setup:settings:whoCanViewMembership': 'ALL_IN_DOMAIN_CAN_VIEW',
                'setup:members': [
                    factories.GoogleGroupMemberFactory.create().as_dict(),
                ],
                'setup:membership:role': 'MEMBER',
                'setup:membership:email': self.by_profile.email,
                'provider_func_args:0': 'setup:group:email',
                'provider_func_args:1': group_containers.MEMBER,
                'assertions:members': lambda x: self.assertEqual(len(x), 1),
            },
            # members only can view, a member
            {
                'setup:group:email': 'group@circlehq.co',
                'setup:settings:whoCanViewMembership': 'ALL_MEMBERS_CAN_VIEW',
                'setup:members': [
                    factories.GoogleGroupMemberFactory.create().as_dict(),
                ],
                'setup:membership:role': 'MEMBER',
                'setup:membership:email': self.by_profile.email,
                'provider_func_args:0': 'setup:group:email',
                'provider_func_args:1': group_containers.MEMBER,
                'assertions:members': lambda x: self.assertEqual(len(x), 1),
            },
            # managers only can view, a member
            {
                'setup:group:email': 'group@circlehq.co',
                'setup:settings:whoCanViewMembership': 'ALL_MANAGERS_CAN_VIEW',
                'setup:members': [
                    factories.GoogleGroupMemberFactory.create().as_dict(),
                ],
                'setup:membership:role': 'MEMBER',
                'setup:membership:email': self.by_profile.email,
                'provider_func_args:0': 'setup:group:email',
                'provider_func_args:1': group_containers.MEMBER,
                'assertions:members': lambda x: self.assertEqual(len(x), 0),
            },
            # all in domain can view, a manager
            {
                'setup:group:email': 'group@circlehq.co',
                'setup:settings:whoCanViewMembership': 'ALL_IN_DOMAIN_CAN_VIEW',
                'setup:members': [
                    factories.GoogleGroupMemberFactory.create().as_dict(),
                ],
                'setup:membership:role': 'MANAGER',
                'setup:membership:email': self.by_profile.email,
                'provider_func_args:0': 'setup:group:email',
                'provider_func_args:1': group_containers.MEMBER,
                'assertions:members': lambda x: self.assertEqual(len(x), 1),
            },
            # members only can view, a manager
            {
                'setup:group:email': 'group@circlehq.co',
                'setup:settings:whoCanViewMembership': 'ALL_MEMBERS_CAN_VIEW',
                'setup:members': [
                    factories.GoogleGroupMemberFactory.create().as_dict(),
                ],
                'setup:membership:role': 'MANAGER',
                'setup:membership:email': self.by_profile.email,
                'provider_func_args:0': 'setup:group:email',
                'provider_func_args:1': group_containers.MEMBER,
                'assertions:members': lambda x: self.assertEqual(len(x), 1),
            },
            # managers only can view, a manager
            {
                'setup:group:email': 'group@circlehq.co',
                'setup:settings:whoCanViewMembership': 'ALL_MANAGERS_CAN_VIEW',
                'setup:members': [
                    factories.GoogleGroupMemberFactory.create().as_dict(),
                ],
                'setup:membership:role': 'MANAGER',
                'setup:membership:email': self.by_profile.email,
                'provider_func_args:0': 'setup:group:email',
                'provider_func_args:1': group_containers.MEMBER,
                'assertions:members': lambda x: self.assertEqual(len(x), 1),
            },
            # all in domain can view, a owner
            {
                'setup:group:email': 'group@circlehq.co',
                'setup:settings:whoCanViewMembership': 'ALL_IN_DOMAIN_CAN_VIEW',
                'setup:members': [
                    factories.GoogleGroupMemberFactory.create().as_dict(),
                ],
                'setup:membership:role': 'OWNER',
                'setup:membership:email': self.by_profile.email,
                'provider_func_args:0': 'setup:group:email',
                'provider_func_args:1': group_containers.MEMBER,
                'assertions:members': lambda x: self.assertEqual(len(x), 1),
            },
            # members only can view, a owner
            {
                'setup:group:email': 'group@circlehq.co',
                'setup:settings:whoCanViewMembership': 'ALL_MEMBERS_CAN_VIEW',
                'setup:members': [
                    factories.GoogleGroupMemberFactory.create().as_dict(),
                ],
                'setup:membership:role': 'OWNER',
                'setup:membership:email': self.by_profile.email,
                'provider_func_args:0': 'setup:group:email',
                'provider_func_args:1': group_containers.MEMBER,
                'assertions:members': lambda x: self.assertEqual(len(x), 1),
            },
            # managers only can view, a owner
            {
                'setup:group:email': 'group@circlehq.co',
                'setup:settings:whoCanViewMembership': 'ALL_MANAGERS_CAN_VIEW',
                'setup:members': [
                    factories.GoogleGroupMemberFactory.create().as_dict(),
                ],
                'setup:membership:role': 'OWNER',
                'setup:membership:email': self.by_profile.email,
                'provider_func_args:0': 'setup:group:email',
                'provider_func_args:1': group_containers.MEMBER,
                'assertions:members': lambda x: self.assertEqual(len(x), 1),
            },
        ]
        self._execute_test_cases('list_members_for_group', test_cases)

    def test_get_group_members_called_with_google_group_role(self):
        @patch.object(self.provider, '_get_group_members')
        @patch.object(self.provider, 'is_group_visible')
        @patch.object(self.provider, '_get_groups_settings_and_membership')
        def test(container_role, expected_role, mock_settings, mock_visible, mock_members):
            mock_settings.return_value = ({'group@circlhq.co': {}}, {})
            mock_visible.return_value = True
            self.provider.list_members_for_group('group@circlehq.co', container_role)
            self.assertEqual(mock_members.call_args[0][1], expected_role)

        test(group_containers.MEMBER, 'MEMBER')
        test(group_containers.OWNER, 'OWNER')
        test(group_containers.MANAGER, 'MANAGER')

    def test_get_group_members_none(self):

        @patch('group.providers.google.build')
        @patch.object(self.provider, 'is_group_visible')
        @patch.object(self.provider, '_get_groups_settings_and_membership')
        def test(mock_settings, mock_visible, mock_api_builder):
            mock_settings.return_value = ({'group@circlhq.co': {}}, {})
            mock_visible.return_value = True
            mock_api_builder().members().list().execute.return_value = {
                'kind': 'admin#directory#members',
            }
            members = self.provider.list_members_for_group('group@circlehq.co', 0)
            self.assertEqual(members, [])
        test()


class TestGoogleGroups(BaseGoogleCase):

    def test_leave_group_not_a_member(self):
        with patch('group.providers.google.build') as patched_build_api:
            patched_build_api().members().delete.side_effect = HttpError('404', 'Error')
            self.provider.leave_group('group@circlehq.co')

    def test_leave_group(self):
        with patch('group.providers.google.build') as patched_build_api:
            patched_build_api().members().delete.return_value = ''
            self.provider.leave_group('group@circlehq.co')
