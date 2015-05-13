from mock import patch
from pprint import pprint

from protobufs.services.group import containers_pb2 as group_containers

from services.test import TestCase
from services.test import mocks

from .. import factories
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
        self.provider = Provider(self.by_profile, self.organization)

    def _structure_fixtures(self, groups, membership=None, members=None):
        if membership is None:
            membership = {}

        if members is None:
            members = tuple()

        return {
            'groups': factories.GoogleProviderGroupsFactory(groups).as_dict(),
            'settings': dict((x.email, x.settings.as_dict()) for x in groups),
            'membership': membership,
            'members': members,
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

            fixtures = self._structure_fixtures([group], membership=membership, members=members)
            try:
                self._execute_test(
                    provider_func_name,
                    test_case['assertions'],
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

        @patch.object(self.provider, '_get_group', return_value=fixtures['groups']['groups'][0])
        @patch.object(self.provider, '_get_groups', return_value=fixtures['groups'])
        @patch.object(
            self.provider,
            '_get_groups_settings_and_membership',
            return_value=(fixtures['settings'], fixtures['membership']),
        )
        def test(*patches):
            result = getattr(self.provider, provider_func_name)(*provider_func_args)
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
        test()

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
            # create a public group
            factories.GoogleGroupFactory(
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
            self.assertEqual(len(groups), 1)
            group = groups[0]
            self.assertTrue(group.can_join)
            self.assertFalse(group.is_member)

        self._execute_test(
            'list_groups_for_profile',
            assertions,
            self._structure_fixtures(groups),
            provider_func_args=(self.for_profile,),
        )


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

        @patch.object(self.provider, '_get_group_members', return_value=fixtures['members'])
        @patch.object(
            self.provider,
            '_get_groups_settings_and_membership',
            return_value=(fixtures['settings'], fixtures['membership']),
        )
        def test(*patches):
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
        test()

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
