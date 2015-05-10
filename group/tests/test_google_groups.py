from mock import patch
from pprint import pprint

from services.test import TestCase
from services.test import mocks

from .. import factories
from ..providers.google import Provider


class TestGoogleGroups(TestCase):

    def setUp(self):
        super(TestGoogleGroups, self).setUp()
        self.organization = mocks.mock_organization()
        self.for_profile = mocks.mock_profile(
            email='michael@circlehq.co',
            organization_id=self.organization.id,
        )
        self.by_profile = mocks.mock_profile(
            email='ravi@circlehq.co',
            organization_id=self.organization.id,
        )
        self.provider = Provider(self.organization, self.by_profile)

    def _execute_test(self, assertions, fixtures):
        @patch.object(self.provider, '_get_provider_groups', return_value=fixtures['groups'])
        @patch.object(
            self.provider,
            '_get_groups_settings_and_membership',
            return_value=(fixtures['settings'], fixtures['membership']),
        )
        def test(*patches):
            groups = self.provider.list_for_profile(self.for_profile)
            if callable(assertions):
                assertions(groups)
            else:
                try:
                    group = groups[0]
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

    def _structure_fixtures(self, groups, membership=None):
        if membership is None:
            membership = {}

        return {
            'groups': factories.GoogleProviderGroupsFactory(groups).as_dict(),
            'settings': dict((x.email, x.settings.as_dict()) for x in groups),
            'membership': membership,
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
        return test_case

    def _execute_test_cases(self, test_cases):
        # TODO switch to generator test case
        for test_case in test_cases:
            test_case = self._parse_test_case(test_case)
            setup = test_case.get('setup', {})
            settings = setup.get('settings', {})
            membership = setup.get('membership', {})

            group_kwargs = {}
            for key, value in settings.iteritems():
                group_kwargs['settings__%s' % (key,)] = value

            group = factories.GoogleGroupFactory(**group_kwargs)
            if membership:
                membership = {group.email: factories.GoogleGroupMember(**membership).as_dict()}

            fixtures = self._structure_fixtures([group], membership=membership)
            try:
                self._execute_test(test_case['assertions'], fixtures)
            except AssertionError:
                print '\nTest Case Failed:'
                pprint(test_case)
                raise

    def test_get_groups_for_user_single_group_cases(self):
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
        self._execute_test_cases(test_cases)

    def test_get_groups_for_user_one_public_one_members_only(self):
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
        self._execute_test(assertions, self._structure_fixtures(groups))
