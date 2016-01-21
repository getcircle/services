import contextlib
from functools import partial
from mock import (
    MagicMock,
    patch,
)
from pprint import pprint
import unittest

from apiclient.errors import HttpError
from protobufs.services.group import containers_pb2 as group_containers

from services.test import (
    fuzzy,
    mocks,
    TestCase,
)

from .. import models
from ..factories import provider as provider_factories
from ..factories import models as model_factories
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
        self.provider = Provider(
            token,
            requester_profile=self.by_profile,
            integration=MagicMock(),
        )

    def _structure_fixtures(self, groups, membership=None, members=None):
        if membership is None:
            membership = {}

        if members is None:
            members = tuple()

        return {
            'groups': provider_factories.GoogleProviderGroupsFactory(groups).as_dict(),
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
            **kwargs
        ):
        # TODO switch to generator test case
        for test_case in test_cases:
            test_case = self._parse_test_case(test_case)
            setup = test_case.get('setup', {})
            membership = setup.get('membership', {})
            members = setup.get('members', [])
            func_args = None
            if provider_func_args is None and 'provider_func_args' in test_case:
                func_args = test_case['provider_func_args']
                func_args = [x[1] for x in sorted(
                    func_args.items(),
                    key=lambda x: x[0],
                )]

            group = model_factories.GoogleGroupFactory.create(
                organization_id=self.organization.id,
                **setup.get('group', {})
            )
            if membership:
                model_factories.GoogleGroupMemberFactory.create(
                    group=group,
                    organization_id=group.organization_id,
                    **membership
                )

            member_models = []
            if members:
                models.GoogleGroupMember.objects.filter(group_id=group.id).delete()
                for member in members:
                    member_models.append(
                        model_factories.GoogleGroupMemberFactory.create(
                            organization_id=group.organization_id,
                            group=group,
                            **member
                        )
                    )

            fixtures = self._structure_fixtures(
                [group],
                members=member_models,
            )
            try:
                self._execute_test(
                    provider_func_name,
                    test_case.get('assertions'),
                    fixtures,
                    provider_func_args=provider_func_args or func_args,
                    test_func=test_func,
                    test_case=test_case,
                )
            except AssertionError:
                print '\nTest Case Failed:'
                pprint(test_case)
                raise
            else:
                group.delete()


@unittest.skip('skip')
@patch('group.providers.google.provider.service.control.get_object')
@patch('group.providers.google.provider.SignedJwtAssertionCredentials')
class TestGoogleGetGroups(BaseGoogleCase):

    def _execute_test(
            self,
            provider_func_name,
            assertions,
            fixtures,
            provider_func_args=None,
            test_func=None,
            **kwargs
        ):
        if provider_func_args is None:
            provider_func_args = tuple()

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
            test_func(assertions, result, **kwargs)
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
                        try:
                            self.assertEqual(getattr(group, key), value)
                        except AssertionError:
                            raise AssertionError(
                                'Expected: %s to equal %s (got %s)' % (
                                    key,
                                    value,
                                    getattr(group, key),
                                )
                            )

    def test_get_groups_with_ids(self, *patches):
        groups = []
        for i in range(4):
            show_group = bool(i % 2)
            group_kwargs = {
                'settings': {
                    'showInGroupDirectory': str(show_group).lower(),
                },
                'organization_id': self.organization.id,
            }
            groups.append(
                model_factories.GoogleGroupFactory.create(
                    **group_kwargs
                )
            )
        groups = self.provider.get_groups_with_ids([group.id for group in groups])
        self.assertEqual(len(groups), 2)

    def test_get_groups_for_organization_cases(self, *patches):
        request = model_factories.GroupMembershipRequestFactory.create(
            requester_profile_id=self.by_profile.id,
            status=group_containers.PENDING,
            provider=group_containers.GOOGLE,
        )
        test_cases = [
            {
                'setup:group:settings:whoCanJoin': 'INVITED_CAN_JOIN',
                'setup:group:settings:whoCanViewMembership': 'ALL_MANAGERS_CAN_VIEW',
                'setup:group:settings:showInGroupDirectory': 'false',
                'assertions:group:can_view': False,
            },
            {
                'setup:group:id': request.group_id,
                'setup:group:settings:whoCanJoin': 'CAN_REQUEST_TO_JOIN',
                'setup:group:settings:whoCanViewMembership': 'ALL_MANAGERS_CAN_VIEW',
                'setup:group:settings:showInGroupDirectory': 'true',
                'assertions:group:can_view': True,
                'assertions:group:has_pending_request': True,
            },
        ]
        self._execute_test_cases('get_groups_for_organization', test_cases)

    def test_get_group(self, *patches):
        request = model_factories.GroupMembershipRequestFactory.create(
            requester_profile_id=self.by_profile.id,
            status=group_containers.PENDING,
            provider=group_containers.GOOGLE,
        )
        test_cases = [
            {
                'setup:group:id': fuzzy.FuzzyUUID().fuzz(),
                'setup:group:settings:whoCanJoin': 'INVITED_CAN_JOIN',
                'setup:group:settings:whoCanViewMembership': 'ALL_MANAGERS_CAN_VIEW',
                'setup:group:settings:showInGroupDirectory': 'false',
                'provider_func_args:0': 'setup:group:id',
                'assertions:group:can_view': False,
                'assertions:group:can_join': False,
                'assertions:group:can_request': False,
                'assertions:group:is_member': False,
                'assertions:group:is_manager': False,
            },
            {
                'setup:group:id': request.group_id,
                'setup:group:settings:whoCanJoin': 'CAN_REQUEST_TO_JOIN',
                'setup:group:settings:whoCanViewMembership': 'ALL_IN_DOMAIN_CAN_VIEW',
                'setup:group:settings:showInGroupDirectory': 'true',
                'provider_func_args:0': 'setup:group:id',
                'assertions:group:can_view': True,
                'assertions:group:can_join': False,
                'assertions:group:can_request': True,
                'assertions:group:is_member': False,
                'assertions:group:is_manager': False,
                'assertions:group:has_pending_request': True,
            },
            {
                'setup:group:id': fuzzy.FuzzyUUID().fuzz(),
                'setup:group:settings:whoCanJoin': 'INVITED_CAN_JOIN',
                'setup:group:settings:whoCanViewMembership': 'ALL_MANAGERS_CAN_VIEW',
                'setup:group:settings:showInGroupDirectory': 'true',
                'setup:group:settings:whoCanInvite': 'ALL_MEMBERS_CAN_INVITE',
                'provider_func_args:0': 'setup:group:id',
                'setup:membership:role': 'MEMBER',
                'setup:membership:profile_id': self.by_profile.id,
                'assertions:group:can_view': True,
                'assertions:group:can_join': False,
                'assertions:group:can_request': False,
                'assertions:group:is_member': True,
                'assertions:group:is_manager': False,
                'assertions:group:has_pending_request': False,
                'assertions:group:permissions:can_add': True,
            },
            {
                'setup:group:id': fuzzy.FuzzyUUID().fuzz(),
                'setup:group:settings:whoCanJoin': 'INVITED_CAN_JOIN',
                'setup:group:settings:whoCanViewMembership': 'ALL_MANAGERS_CAN_VIEW',
                'setup:group:settings:showInGroupDirectory': 'true',
                'setup:group:settings:whoCanInvite': 'ALL_MANAGERS_CAN_INVITE',
                'provider_func_args:0': 'setup:group:id',
                'setup:membership:role': 'MEMBER',
                'setup:membership:profile_id': self.by_profile.id,
                'assertions:group:can_view': True,
                'assertions:group:can_join': False,
                'assertions:group:can_request': False,
                'assertions:group:is_member': True,
                'assertions:group:is_manager': False,
                'assertions:group:has_pending_request': False,
                'assertions:group:permissions:can_add': False,
            },
            {
                'setup:group:id': fuzzy.FuzzyUUID().fuzz(),
                'setup:group:settings:whoCanJoin': 'INVITED_CAN_JOIN',
                'setup:group:settings:whoCanViewMembership': 'ALL_MANAGERS_CAN_VIEW',
                'setup:group:settings:showInGroupDirectory': 'true',
                'setup:group:settings:whoCanInvite': 'ALL_MANAGERS_CAN_INVITE',
                'provider_func_args:0': 'setup:group:id',
                'setup:membership:role': 'MANAGER',
                'setup:membership:profile_id': self.by_profile.id,
                'assertions:group:can_view': True,
                'assertions:group:can_join': False,
                'assertions:group:can_request': False,
                'assertions:group:is_member': True,
                'assertions:group:is_manager': True,
                'assertions:group:has_pending_request': False,
                'assertions:group:permissions:can_add': True,
            },
            {
                'setup:group:id': fuzzy.FuzzyUUID().fuzz(),
                'setup:group:settings:whoCanJoin': 'INVITED_CAN_JOIN',
                'setup:group:settings:whoCanViewMembership': 'ALL_MANAGERS_CAN_VIEW',
                'setup:group:settings:showInGroupDirectory': 'true',
                'setup:group:settings:whoCanInvite': 'ALL_MANAGERS_CAN_INVITE',
                'provider_func_args:0': 'setup:group:id',
                'setup:membership:role': 'OWNER',
                'setup:membership:profile_id': self.by_profile.id,
                'assertions:group:can_view': True,
                'assertions:group:can_join': False,
                'assertions:group:can_request': False,
                'assertions:group:is_member': True,
                'assertions:group:is_manager': True,
                'assertions:group:permissions:can_add': True,
            },
        ]

        def test(assertions, result, **kwargs):
            if not assertions['group']['can_view'] and result is not None:
                raise AssertionError('Group should not have been visible')
            elif assertions['group']['can_view'] and result is None:
                raise AssertionError('Group should be visible')

            for key, value in assertions['group'].iteritems():
                if isinstance(value, dict):
                    continue

                if hasattr(result, key):
                    try:
                        self.assertEqual(getattr(result, key), value)
                    except AssertionError:
                        raise AssertionError('Expected "%s" to equal: %s (got %s)' % (
                            key,
                            value,
                            getattr(result, key),
                        ))

            if result:
                is_manager = assertions.get('group', {}).get('is_manager', False)
                if is_manager:
                    self.assertTrue(result.permissions.can_edit)
                    self.assertFalse(result.permissions.can_delete)
                    can_add = assertions.get('group', {}).get('permissions', {}).get('can_add')
                    if can_add is not None:
                        self.assertEqual(result.permissions.can_add, can_add)
                else:
                    self.assertFalse(result.permissions.can_edit)
                    self.assertFalse(result.permissions.can_delete)
                    self.assertFalse(result.permissions.can_add)

        self._execute_test_cases('get_group', test_cases, test_func=test)

    def test_get_groups_for_user_single_group_cases(self, *patches):
        request = model_factories.GroupMembershipRequestFactory.create(
            requester_profile_id=self.by_profile.id,
            status=group_containers.PENDING,
            provider=group_containers.GOOGLE,
        )
        test_cases = [
            {
                'setup:group:settings:whoCanJoin': 'ALL_IN_DOMAIN_CAN_JOIN',
                'setup:group:settings:whoCanViewMembership': 'ALL_IN_DOMAIN_CAN_VIEW',
                'setup:membership:role': 'MEMBER',
                'setup:membership:profile_id': self.for_profile.id,
                'assertions:group:can_join': True,
                'assertions:group:can_request': False,
                'assertions:group:is_member': False,
                'assertions:group:is_manager': False,
                'assertions:group:can_view': True,
            },
            {
                'setup:group:settings:whoCanJoin': 'ALL_IN_DOMAIN_CAN_JOIN',
                'setup:group:settings:whoCanViewMembership': 'ALL_MEMBERS_CAN_VIEW',
                'setup:membership:role': 'MEMBER',
                'setup:membership:profile_id': self.for_profile.id,
                'assertions:group:can_join': True,
                'assertions:group:can_request': False,
                'assertions:group:is_member': False,
                'assertions:group:is_manager': False,
                'assertions:group:can_view': False,
            },
            {
                'setup:group:settings:whoCanJoin': 'ALL_IN_DOMAIN_CAN_JOIN',
                'setup:group:settings:whoCanViewMembership': 'ALL_MANAGERS_CAN_VIEW',
                'setup:membership:role': 'MEMBER',
                'setup:membership:profile_id': self.for_profile.id,
                'assertions:group:can_join': True,
                'assertions:group:can_request': False,
                'assertions:group:is_member': False,
                'assertions:group:is_manager': False,
                'assertions:group:can_view': False,
            },
            {
                'setup:group:settings:whoCanJoin': 'ANYONE_CAN_JOIN',
                'setup:group:settings:whoCanViewMembership': 'ALL_IN_DOMAIN_CAN_VIEW',
                'setup:membership:role': 'MEMBER',
                'setup:membership:profile_id': self.for_profile.id,
                'assertions:group:can_join': True,
                'assertions:group:can_request': False,
                'assertions:group:is_member': False,
                'assertions:group:is_manager': False,
                'assertions:group:can_view': True,
            },
            {
                'setup:group:settings:whoCanJoin': 'ANYONE_CAN_JOIN',
                'setup:group:settings:whoCanViewMembership': 'ALL_MEMBERS_CAN_VIEW',
                'setup:membership:role': 'MEMBER',
                'setup:membership:profile_id': self.for_profile.id,
                'assertions:group:can_join': True,
                'assertions:group:can_request': False,
                'assertions:group:is_member': False,
                'assertions:group:is_manager': False,
                'assertions:group:can_view': False,
            },
            {
                'setup:group:settings:whoCanJoin': 'ANYONE_CAN_JOIN',
                'setup:group:settings:whoCanViewMembership': 'ALL_MANAGERS_CAN_VIEW',
                'setup:membership:role': 'MEMBER',
                'setup:membership:profile_id': self.for_profile.id,
                'assertions:group:can_join': True,
                'assertions:group:can_request': False,
                'assertions:group:is_member': False,
                'assertions:group:is_manager': False,
                'assertions:group:can_view': False,
            },
            {
                'setup:group:id': request.group_id,
                'setup:group:settings:whoCanJoin': 'CAN_REQUEST_TO_JOIN',
                'setup:group:settings:whoCanViewMembership': 'ALL_IN_DOMAIN_CAN_VIEW',
                'setup:membership:role': 'MEMBER',
                'setup:membership:profile_id': self.for_profile.id,
                'assertions:group:can_join': False,
                'assertions:group:can_request': True,
                'assertions:group:is_member': False,
                'assertions:group:is_manager': False,
                'assertions:group:can_view': True,
                'assertions:group:has_pending_request': True,
            },
            {
                'setup:group:settings:whoCanJoin': 'ANYONE_CAN_JOIN',
                'setup:group:settings:whoCanViewMembership': 'ALL_MEMBERS_CAN_VIEW',
                'setup:membership:role': 'MEMBER',
                'setup:membership:profile_id': self.for_profile.id,
                'assertions:group:can_join': True,
                'assertions:group:can_request': False,
                'assertions:group:is_member': False,
                'assertions:group:is_manager': False,
                'assertions:group:can_view': False,
            },
            {
                'setup:group:settings:whoCanJoin': 'ANYONE_CAN_JOIN',
                'setup:group:settings:whoCanViewMembership': 'ALL_MANAGERS_CAN_VIEW',
                'setup:membership:role': 'MEMBER',
                'setup:membership:profile_id': self.for_profile.id,
                'assertions:group:can_join': True,
                'assertions:group:can_request': False,
                'assertions:group:is_member': False,
                'assertions:group:is_manager': False,
                'assertions:group:can_view': False,
            },
            {
                'setup:group:settings:whoCanJoin': 'INVITED_CAN_JOIN',
                'setup:group:settings:whoCanViewMembership': 'ALL_IN_DOMAIN_CAN_VIEW',
                'setup:membership:role': 'MEMBER',
                'setup:membership:profile_id': self.for_profile.id,
                'assertions:group:can_join': False,
                'assertions:group:can_request': False,
                'assertions:group:is_member': False,
                'assertions:group:is_manager': False,
                'assertions:group:can_view': True,
            },
            {
                'setup:group:settings:whoCanJoin': 'INVITED_CAN_JOIN',
                'setup:group:settings:whoCanViewMembership': 'ALL_MEMBERS_CAN_VIEW',
                'setup:membership:role': 'MEMBER',
                'setup:membership:profile_id': self.for_profile.id,
                'assertions:group:can_join': False,
                'assertions:group:can_request': False,
                'assertions:group:is_member': False,
                'assertions:group:is_manager': False,
                'assertions:group:can_view': False,
            },
            {
                'setup:group:settings:whoCanJoin': 'INVITED_CAN_JOIN',
                'setup:group:settings:whoCanViewMembership': 'ALL_MANAGERS_CAN_VIEW',
                'setup:membership:role': 'MEMBER',
                'setup:membership:profile_id': self.for_profile.id,
                'assertions:group:can_join': False,
                'assertions:group:can_request': False,
                'assertions:group:is_member': False,
                'assertions:group:is_manager': False,
                'assertions:group:can_view': False,
            },
            {
                'setup:group:settings:whoCanJoin': 'ALL_IN_DOMAIN_CAN_JOIN',
                'setup:group:settings:whoCanViewMembership': 'ALL_IN_DOMAIN_CAN_VIEW',
                'setup:members': [
                    {'role': 'MEMBER', 'profile_id': self.by_profile.id},
                    {'role': 'MEMBER', 'profile_id': self.for_profile.id},
                ],
                'assertions:group:can_join': False,
                'assertions:group:can_request': False,
                'assertions:group:is_member': True,
                'assertions:group:is_manager': False,
                'assertions:group:can_view': True,
            },
            {
                'setup:group:settings:whoCanJoin': 'ALL_IN_DOMAIN_CAN_JOIN',
                'setup:group:settings:whoCanViewMembership': 'ALL_MEMBERS_CAN_VIEW',
                'setup:members': [
                    {'role': 'MEMBER', 'profile_id': self.by_profile.id},
                    {'role': 'MEMBER', 'profile_id': self.for_profile.id},
                ],
                'assertions:group:can_join': False,
                'assertions:group:can_request': False,
                'assertions:group:is_member': True,
                'assertions:group:is_manager': False,
                'assertions:group:can_view': True,
            },
            {
                'setup:group:settings:whoCanJoin': 'ALL_IN_DOMAIN_CAN_JOIN',
                'setup:group:settings:whoCanViewMembership': 'ALL_MANAGERS_CAN_VIEW',
                'setup:members': [
                    {'role': 'MEMBER', 'profile_id': self.by_profile.id},
                    {'role': 'MEMBER', 'profile_id': self.for_profile.id},
                ],
                'assertions:group:can_join': False,
                'assertions:group:can_request': False,
                'assertions:group:is_member': True,
                'assertions:group:is_manager': False,
                'assertions:group:can_view': False,
            },
            {
                'setup:group:settings:whoCanJoin': 'ANYONE_CAN_JOIN',
                'setup:group:settings:whoCanViewMembership': 'ALL_IN_DOMAIN_CAN_VIEW',
                'setup:members': [
                    {'role': 'MEMBER', 'profile_id': self.by_profile.id},
                    {'role': 'MEMBER', 'profile_id': self.for_profile.id},
                ],
                'assertions:group:can_join': False,
                'assertions:group:can_request': False,
                'assertions:group:is_member': True,
                'assertions:group:is_manager': False,
                'assertions:group:can_view': True,
            },
            {
                'setup:group:settings:whoCanJoin': 'ANYONE_CAN_JOIN',
                'setup:group:settings:whoCanViewMembership': 'ALL_MEMBERS_CAN_VIEW',
                'setup:members': [
                    {'role': 'MEMBER', 'profile_id': self.by_profile.id},
                    {'role': 'MEMBER', 'profile_id': self.for_profile.id},
                ],
                'assertions:group:can_join': False,
                'assertions:group:can_request': False,
                'assertions:group:is_member': True,
                'assertions:group:is_manager': False,
                'assertions:group:can_view': True,
            },
            {
                'setup:group:settings:whoCanJoin': 'ANYONE_CAN_JOIN',
                'setup:group:settings:whoCanViewMembership': 'ALL_MANAGERS_CAN_VIEW',
                'setup:members': [
                    {'role': 'MEMBER', 'profile_id': self.by_profile.id},
                    {'role': 'MEMBER', 'profile_id': self.for_profile.id},
                ],
                'assertions:group:can_join': False,
                'assertions:group:can_request': False,
                'assertions:group:is_member': True,
                'assertions:group:is_manager': False,
                'assertions:group:can_view': False,
            },
            {
                'setup:group:settings:whoCanJoin': 'CAN_REQUEST_TO_JOIN',
                'setup:group:settings:whoCanViewMembership': 'ALL_IN_DOMAIN_CAN_VIEW',
                'setup:members': [
                    {'role': 'MEMBER', 'profile_id': self.by_profile.id},
                    {'role': 'MEMBER', 'profile_id': self.for_profile.id},
                ],
                'assertions:group:can_join': False,
                'assertions:group:can_request': False,
                'assertions:group:is_member': True,
                'assertions:group:is_manager': False,
                'assertions:group:can_view': True,
            },
            {
                'setup:group:settings:whoCanJoin': 'CAN_REQUEST_TO_JOIN',
                'setup:group:settings:whoCanViewMembership': 'ALL_MEMBERS_CAN_VIEW',
                'setup:members': [
                    {'role': 'MEMBER', 'profile_id': self.by_profile.id},
                    {'role': 'MEMBER', 'profile_id': self.for_profile.id},
                ],
                'assertions:group:can_join': False,
                'assertions:group:can_request': False,
                'assertions:group:is_member': True,
                'assertions:group:is_manager': False,
                'assertions:group:can_view': True,
            },
            {
                'setup:group:settings:whoCanJoin': 'CAN_REQUEST_TO_JOIN',
                'setup:group:settings:whoCanViewMembership': 'ALL_MANAGERS_CAN_VIEW',
                'setup:members': [
                    {'role': 'MEMBER', 'profile_id': self.by_profile.id},
                    {'role': 'MEMBER', 'profile_id': self.for_profile.id},
                ],
                'assertions:group:can_join': False,
                'assertions:group:can_request': False,
                'assertions:group:is_member': True,
                'assertions:group:is_manager': False,
                'assertions:group:can_view': False,
            },
            {
                'setup:group:settings:whoCanJoin': 'INVITED_CAN_JOIN',
                'setup:group:settings:whoCanViewMembership': 'ALL_IN_DOMAIN_CAN_VIEW',
                'setup:members': [
                    {'role': 'MEMBER', 'profile_id': self.by_profile.id},
                    {'role': 'MEMBER', 'profile_id': self.for_profile.id},
                ],
                'assertions:group:can_join': False,
                'assertions:group:can_request': False,
                'assertions:group:is_member': True,
                'assertions:group:is_manager': False,
                'assertions:group:can_view': True,
            },
            {
                'setup:group:settings:whoCanJoin': 'INVITED_CAN_JOIN',
                'setup:group:settings:whoCanViewMembership': 'ALL_MEMBERS_CAN_VIEW',
                'setup:members': [
                    {'role': 'MEMBER', 'profile_id': self.by_profile.id},
                    {'role': 'MEMBER', 'profile_id': self.for_profile.id},
                ],
                'assertions:group:can_join': False,
                'assertions:group:can_request': False,
                'assertions:group:is_member': True,
                'assertions:group:is_manager': False,
                'assertions:group:can_view': True,
            },
            {
                'setup:group:settings:whoCanJoin': 'INVITED_CAN_JOIN',
                'setup:group:settings:whoCanViewMembership': 'ALL_MANAGERS_CAN_VIEW',
                'setup:members': [
                    {'role': 'MEMBER', 'profile_id': self.by_profile.id},
                    {'role': 'MEMBER', 'profile_id': self.for_profile.id},
                ],
                'assertions:group:can_join': False,
                'assertions:group:can_request': False,
                'assertions:group:is_member': True,
                'assertions:group:is_manager': False,
                'assertions:group:can_view': False,
            },
            {
                'setup:group:settings:whoCanJoin': 'ALL_IN_DOMAIN_CAN_JOIN',
                'setup:group:settings:whoCanViewMembership': 'ALL_IN_DOMAIN_CAN_VIEW',
                'setup:members': [
                    {'role': 'MANAGER', 'profile_id': self.by_profile.id},
                    {'role': 'MEMBER', 'profile_id': self.for_profile.id},
                ],
                'assertions:group:can_join': False,
                'assertions:group:can_request': False,
                'assertions:group:is_member': True,
                'assertions:group:is_manager': True,
                'assertions:group:can_view': True,
            },
            {
                'setup:group:settings:whoCanJoin': 'ALL_IN_DOMAIN_CAN_JOIN',
                'setup:group:settings:whoCanViewMembership': 'ALL_MEMBERS_CAN_VIEW',
                'setup:members': [
                    {'role': 'MANAGER', 'profile_id': self.by_profile.id},
                    {'role': 'MEMBER', 'profile_id': self.for_profile.id},
                ],
                'assertions:group:can_join': False,
                'assertions:group:can_request': False,
                'assertions:group:is_member': True,
                'assertions:group:is_manager': True,
                'assertions:group:can_view': True,
            },
            {
                'setup:group:settings:whoCanJoin': 'ALL_IN_DOMAIN_CAN_JOIN',
                'setup:group:settings:whoCanViewMembership': 'ALL_MANAGERS_CAN_VIEW',
                'setup:members': [
                    {'role': 'MANAGER', 'profile_id': self.by_profile.id},
                    {'role': 'MEMBER', 'profile_id': self.for_profile.id},
                ],
                'assertions:group:can_join': False,
                'assertions:group:can_request': False,
                'assertions:group:is_member': True,
                'assertions:group:is_manager': True,
                'assertions:group:can_view': True,
            },
            {
                'setup:group:settings:whoCanJoin': 'ANYONE_CAN_JOIN',
                'setup:group:settings:whoCanViewMembership': 'ALL_IN_DOMAIN_CAN_VIEW',
                'setup:members': [
                    {'role': 'MANAGER', 'profile_id': self.by_profile.id},
                    {'role': 'MEMBER', 'profile_id': self.for_profile.id},
                ],
                'assertions:group:can_join': False,
                'assertions:group:can_request': False,
                'assertions:group:is_member': True,
                'assertions:group:is_manager': True,
                'assertions:group:can_view': True,
            },
            {
                'setup:group:settings:whoCanJoin': 'ANYONE_CAN_JOIN',
                'setup:group:settings:whoCanViewMembership': 'ALL_MEMBERS_CAN_VIEW',
                'setup:members': [
                    {'role': 'MANAGER', 'profile_id': self.by_profile.id},
                    {'role': 'MEMBER', 'profile_id': self.for_profile.id},
                ],
                'assertions:group:can_join': False,
                'assertions:group:can_request': False,
                'assertions:group:is_member': True,
                'assertions:group:is_manager': True,
                'assertions:group:can_view': True,
            },
            {
                'setup:group:settings:whoCanJoin': 'ANYONE_CAN_JOIN',
                'setup:group:settings:whoCanViewMembership': 'ALL_MANAGERS_CAN_VIEW',
                'setup:members': [
                    {'role': 'MANAGER', 'profile_id': self.by_profile.id},
                    {'role': 'MEMBER', 'profile_id': self.for_profile.id},
                ],
                'assertions:group:can_join': False,
                'assertions:group:can_request': False,
                'assertions:group:is_member': True,
                'assertions:group:is_manager': True,
                'assertions:group:can_view': True,
            },
            {
                'setup:group:settings:whoCanJoin': 'CAN_REQUEST_TO_JOIN',
                'setup:group:settings:whoCanViewMembership': 'ALL_IN_DOMAIN_CAN_VIEW',
                'setup:members': [
                    {'role': 'MANAGER', 'profile_id': self.by_profile.id},
                    {'role': 'MEMBER', 'profile_id': self.for_profile.id},
                ],
                'assertions:group:can_join': False,
                'assertions:group:can_request': False,
                'assertions:group:is_member': True,
                'assertions:group:is_manager': True,
                'assertions:group:can_view': True,
            },
            {
                'setup:group:settings:whoCanJoin': 'CAN_REQUEST_TO_JOIN',
                'setup:group:settings:whoCanViewMembership': 'ALL_MEMBERS_CAN_VIEW',
                'setup:members': [
                    {'role': 'MANAGER', 'profile_id': self.by_profile.id},
                    {'role': 'MEMBER', 'profile_id': self.for_profile.id},
                ],
                'assertions:group:can_join': False,
                'assertions:group:can_request': False,
                'assertions:group:is_member': True,
                'assertions:group:is_manager': True,
                'assertions:group:can_view': True,
            },
            {
                'setup:group:settings:whoCanJoin': 'CAN_REQUEST_TO_JOIN',
                'setup:group:settings:whoCanViewMembership': 'ALL_MANAGERS_CAN_VIEW',
                'setup:members': [
                    {'role': 'MANAGER', 'profile_id': self.by_profile.id},
                    {'role': 'MEMBER', 'profile_id': self.for_profile.id},
                ],
                'assertions:group:can_join': False,
                'assertions:group:can_request': False,
                'assertions:group:is_member': True,
                'assertions:group:is_manager': True,
                'assertions:group:can_view': True,
            },
            {
                'setup:group:settings:whoCanJoin': 'INVITED_CAN_JOIN',
                'setup:group:settings:whoCanViewMembership': 'ALL_IN_DOMAIN_CAN_VIEW',
                'setup:members': [
                    {'role': 'MANAGER', 'profile_id': self.by_profile.id},
                    {'role': 'MEMBER', 'profile_id': self.for_profile.id},
                ],
                'assertions:group:can_join': False,
                'assertions:group:can_request': False,
                'assertions:group:is_member': True,
                'assertions:group:is_manager': True,
                'assertions:group:can_view': True,
            },
            {
                'setup:group:settings:whoCanJoin': 'INVITED_CAN_JOIN',
                'setup:group:settings:whoCanViewMembership': 'ALL_MEMBERS_CAN_VIEW',
                'setup:members': [
                    {'role': 'MANAGER', 'profile_id': self.by_profile.id},
                    {'role': 'MEMBER', 'profile_id': self.for_profile.id},
                ],
                'assertions:group:can_join': False,
                'assertions:group:can_request': False,
                'assertions:group:is_member': True,
                'assertions:group:is_manager': True,
                'assertions:group:can_view': True,
            },
            {
                'setup:group:settings:whoCanJoin': 'INVITED_CAN_JOIN',
                'setup:group:settings:whoCanViewMembership': 'ALL_MANAGERS_CAN_VIEW',
                'setup:members': [
                    {'role': 'MANAGER', 'profile_id': self.by_profile.id},
                    {'role': 'MEMBER', 'profile_id': self.for_profile.id},
                ],
                'assertions:group:can_join': False,
                'assertions:group:can_request': False,
                'assertions:group:is_member': True,
                'assertions:group:is_manager': True,
                'assertions:group:can_view': True,
            },
            {
                'setup:group:settings:whoCanJoin': 'ALL_IN_DOMAIN_CAN_JOIN',
                'setup:group:settings:whoCanViewMembership': 'ALL_IN_DOMAIN_CAN_VIEW',
                'setup:members': [
                    {'role': 'OWNER', 'profile_id': self.by_profile.id},
                    {'role': 'MEMBER', 'profile_id': self.for_profile.id},
                ],
                'assertions:group:can_join': False,
                'assertions:group:can_request': False,
                'assertions:group:is_member': True,
                'assertions:group:is_manager': True,
                'assertions:group:can_view': True,
            },
            {
                'setup:group:settings:whoCanJoin': 'ALL_IN_DOMAIN_CAN_JOIN',
                'setup:group:settings:whoCanViewMembership': 'ALL_MEMBERS_CAN_VIEW',
                'setup:members': [
                    {'role': 'OWNER', 'profile_id': self.by_profile.id},
                    {'role': 'MEMBER', 'profile_id': self.for_profile.id},
                ],
                'assertions:group:can_join': False,
                'assertions:group:can_request': False,
                'assertions:group:is_member': True,
                'assertions:group:is_manager': True,
                'assertions:group:can_view': True,
            },
            {
                'setup:group:settings:whoCanJoin': 'ALL_IN_DOMAIN_CAN_JOIN',
                'setup:group:settings:whoCanViewMembership': 'ALL_MANAGERS_CAN_VIEW',
                'setup:members': [
                    {'role': 'OWNER', 'profile_id': self.by_profile.id},
                    {'role': 'MEMBER', 'profile_id': self.for_profile.id},
                ],
                'assertions:group:can_join': False,
                'assertions:group:can_request': False,
                'assertions:group:is_member': True,
                'assertions:group:is_manager': True,
                'assertions:group:can_view': True,
            },
            {
                'setup:group:settings:whoCanJoin': 'ANYONE_CAN_JOIN',
                'setup:group:settings:whoCanViewMembership': 'ALL_IN_DOMAIN_CAN_VIEW',
                'setup:members': [
                    {'role': 'OWNER', 'profile_id': self.by_profile.id},
                    {'role': 'MEMBER', 'profile_id': self.for_profile.id},
                ],
                'assertions:group:can_join': False,
                'assertions:group:can_request': False,
                'assertions:group:is_member': True,
                'assertions:group:is_manager': True,
                'assertions:group:can_view': True,
            },
            {
                'setup:group:settings:whoCanJoin': 'ANYONE_CAN_JOIN',
                'setup:group:settings:whoCanViewMembership': 'ALL_MEMBERS_CAN_VIEW',
                'setup:members': [
                    {'role': 'OWNER', 'profile_id': self.by_profile.id},
                    {'role': 'MEMBER', 'profile_id': self.for_profile.id},
                ],
                'assertions:group:can_join': False,
                'assertions:group:can_request': False,
                'assertions:group:is_member': True,
                'assertions:group:is_manager': True,
                'assertions:group:can_view': True,
            },
            {
                'setup:group:settings:whoCanJoin': 'ANYONE_CAN_JOIN',
                'setup:group:settings:whoCanViewMembership': 'ALL_MANAGERS_CAN_VIEW',
                'setup:members': [
                    {'role': 'OWNER', 'profile_id': self.by_profile.id},
                    {'role': 'MEMBER', 'profile_id': self.for_profile.id},
                ],
                'assertions:group:can_join': False,
                'assertions:group:can_request': False,
                'assertions:group:is_member': True,
                'assertions:group:is_manager': True,
                'assertions:group:can_view': True,
            },
            {
                'setup:group:settings:whoCanJoin': 'CAN_REQUEST_TO_JOIN',
                'setup:group:settings:whoCanViewMembership': 'ALL_IN_DOMAIN_CAN_VIEW',
                'setup:members': [
                    {'role': 'OWNER', 'profile_id': self.by_profile.id},
                    {'role': 'MEMBER', 'profile_id': self.for_profile.id},
                ],
                'assertions:group:can_join': False,
                'assertions:group:can_request': False,
                'assertions:group:is_member': True,
                'assertions:group:is_manager': True,
                'assertions:group:can_view': True,
            },
            {
                'setup:group:settings:whoCanJoin': 'CAN_REQUEST_TO_JOIN',
                'setup:group:settings:whoCanViewMembership': 'ALL_MEMBERS_CAN_VIEW',
                'setup:members': [
                    {'role': 'OWNER', 'profile_id': self.by_profile.id},
                    {'role': 'MEMBER', 'profile_id': self.for_profile.id},
                ],
                'assertions:group:can_join': False,
                'assertions:group:can_request': False,
                'assertions:group:is_member': True,
                'assertions:group:is_manager': True,
                'assertions:group:can_view': True,
            },
            {
                'setup:group:settings:whoCanJoin': 'CAN_REQUEST_TO_JOIN',
                'setup:group:settings:whoCanViewMembership': 'ALL_MANAGERS_CAN_VIEW',
                'setup:members': [
                    {'role': 'OWNER', 'profile_id': self.by_profile.id},
                    {'role': 'MEMBER', 'profile_id': self.for_profile.id},
                ],
                'assertions:group:can_join': False,
                'assertions:group:can_request': False,
                'assertions:group:is_member': True,
                'assertions:group:is_manager': True,
                'assertions:group:can_view': True,
            },
            {
                'setup:group:settings:whoCanJoin': 'INVITED_CAN_JOIN',
                'setup:group:settings:whoCanViewMembership': 'ALL_IN_DOMAIN_CAN_VIEW',
                'setup:members': [
                    {'role': 'OWNER', 'profile_id': self.by_profile.id},
                    {'role': 'MEMBER', 'profile_id': self.for_profile.id},
                ],
                'assertions:group:can_join': False,
                'assertions:group:can_request': False,
                'assertions:group:is_member': True,
                'assertions:group:is_manager': True,
                'assertions:group:can_view': True,
            },
            {
                'setup:group:settings:whoCanJoin': 'INVITED_CAN_JOIN',
                'setup:group:settings:whoCanViewMembership': 'ALL_MEMBERS_CAN_VIEW',
                'setup:members': [
                    {'role': 'OWNER', 'profile_id': self.by_profile.id},
                    {'role': 'MEMBER', 'profile_id': self.for_profile.id},
                ],
                'assertions:group:can_join': False,
                'assertions:group:can_request': False,
                'assertions:group:is_member': True,
                'assertions:group:is_manager': True,
                'assertions:group:can_view': True,
            },
            {
                'setup:group:settings:whoCanJoin': 'INVITED_CAN_JOIN',
                'setup:group:settings:whoCanViewMembership': 'ALL_MANAGERS_CAN_VIEW',
                'setup:members': [
                    {'role': 'OWNER', 'profile_id': self.by_profile.id},
                    {'role': 'MEMBER', 'profile_id': self.for_profile.id},
                ],
                'assertions:group:can_join': False,
                'assertions:group:can_request': False,
                'assertions:group:is_member': True,
                'assertions:group:is_manager': True,
                'assertions:group:can_view': True,
            },
        ]
        self._execute_test_cases(
            'get_groups_for_profile',
            test_cases,
            provider_func_args=(self.for_profile,),
        )

    def test_get_groups_for_user_one_public_one_members_only(self, *patches):
        groups = [
            # create public groups with alphabetical names
            model_factories.GoogleGroupMemberFactory.create(
                group__name='b',
                group__description='test',
                group__settings={
                    'whoCanJoin': 'ALL_IN_DOMAIN_CAN_JOIN',
                    'whoCanViewMembership': 'ALL_IN_DOMAIN_CAN_VIEW',
                },
                group__organization_id=self.organization.id,
                profile_id=self.for_profile.id,
                organization_id=self.organization.id,
            ),
            model_factories.GoogleGroupMemberFactory.create(
                group__name='a',
                group__settings={
                    'whoCanJoin': 'ALL_IN_DOMAIN_CAN_JOIN',
                    'whoCanViewMembership': 'ALL_IN_DOMAIN_CAN_VIEW',
                },
                group__organization_id=self.organization.id,
                profile_id=self.for_profile.id,
                organization_id=self.organization.id,
            ),
            # create a members only group
            model_factories.GoogleGroupFactory.create(
                settings={
                    'whoCanJoin': 'INVITED_CAN_JOIN',
                    'whoCanViewMembership': 'ALL_MEMBERS_CAN_VIEW',
                },
                organization_id=self.organization.id,
            )
        ]

        def assertions(groups):
            self.assertEqual(len(groups), 2)
            group = groups[0]
            self.assertTrue(group.can_join)
            self.assertFalse(group.is_member)
            self.assertEqual(groups[0].name, 'a')
            self.assertEqual(groups[1].name, 'b')
            self.assertEqual(groups[1].group_description, 'test')

        self._execute_test(
            'get_groups_for_profile',
            assertions,
            self._structure_fixtures(groups),
            provider_func_args=(self.for_profile,),
        )

    def test_get_groups_for_organization_alphabetical(self, *patches):
        groups = [
            # create public groups with alphabetical names
            model_factories.GoogleGroupFactory(
                name='b',
                settings={
                    'whoCanJoin': 'ALL_IN_DOMAIN_CAN_JOIN',
                    'whoCanViewMembership': 'ALL_IN_DOMAIN_CAN_VIEW',
                    'showInGroupDirectory': 'true',
                },
                organization_id=self.organization.id,
            ),
            model_factories.GoogleGroupFactory(
                name='a',
                settings={
                    'whoCanJoin': 'ALL_IN_DOMAIN_CAN_JOIN',
                    'whoCanViewMembership': 'ALL_IN_DOMAIN_CAN_VIEW',
                    'showInGroupDirectory': 'true',
                },
                organization_id=self.organization.id,
            ),
            model_factories.GoogleGroupFactory(
                name='c',
                settings={
                    'whoCanJoin': 'ALL_IN_DOMAIN_CAN_JOIN',
                    'whoCanViewMembership': 'ALL_IN_DOMAIN_CAN_VIEW',
                    'showInGroupDirectory': 'false',
                },
                organization_id=self.organization.id,
            ),
        ]

        def assertions(groups):
            self.assertEqual(len(groups), 2)
            self.assertFalse(groups[0].is_member)
            self.assertEqual(groups[0].name, 'a')
            self.assertEqual(groups[1].name, 'b')

        self._execute_test(
            'get_groups_for_organization',
            assertions,
            self._structure_fixtures(groups),
        )

    def test_join_group(self, *patches):
        test_cases = [
            {
                'setup:group:id': fuzzy.FuzzyUUID().fuzz(),
                'setup:group:settings:whoCanJoin': 'ANYONE_CAN_JOIN',
                'provider_func_args:0': 'setup:group:id',
                'assertions:request:status': group_containers.APPROVED,
                'assertions:request:meta:whoCanJoin': 'ANYONE_CAN_JOIN',
            },
            {
                'setup:group:id': fuzzy.FuzzyUUID().fuzz(),
                'setup:group:settings:whoCanJoin': 'ALL_IN_DOMAIN_CAN_JOIN',
                'provider_func_args:0': 'setup:group:id',
                'assertions:request:status': group_containers.APPROVED,
                'assertions:request:meta:whoCanJoin': 'ALL_IN_DOMAIN_CAN_JOIN',
            },
            {
                'setup:group:id': fuzzy.FuzzyUUID().fuzz(),
                'setup:group:settings:whoCanJoin': 'INVITED_CAN_JOIN',
                'provider_func_args:0': 'setup:group:id',
                'assertions:request:status': group_containers.DENIED,
                'assertions:request:meta:whoCanJoin': 'INVITED_CAN_JOIN',
            },
            {
                'setup:members': [{'role': 'OWNER'}, {'role': 'MANAGER'}, {'role': 'MEMBER'}],
                'setup:group:id': fuzzy.FuzzyUUID().fuzz(),
                'setup:group:settings:whoCanJoin': 'CAN_REQUEST_TO_JOIN',
                'provider_func_args:0': 'setup:group:id',
                'assertions:request:status': group_containers.PENDING,
                'assertions:request:meta:whoCanJoin': 'CAN_REQUEST_TO_JOIN',
                'assertions:request:approver_profile_ids': 2,
            },
        ]

        contexts = [
            self.mock_transport(),
            patch.object(self.provider, '_add_to_group'),
        ]
        with contextlib.nested(*contexts) as (mock, mock_add_to_group):

            def test(assertions, result, **kwargs):
                self.assertEqual(assertions['request']['status'], result.status)
                if assertions['request']['status'] == group_containers.APPROVED:
                    self.assertEqual(mock_add_to_group.call_count, 1)
                    mock_add_to_group.reset_mock()

                self.assertEqual(
                    assertions['request']['meta']['whoCanJoin'],
                    result.meta['whoCanJoin'],
                )
                expected_approver_ids = assertions['request'].get('approver_profile_ids')
                if expected_approver_ids:
                    self.assertEqual(len(result.approver_profile_ids), expected_approver_ids)

            mock.instance.register_mock_object(
                service='profile',
                action='get_profiles',
                return_object_path='profiles',
                return_object=[mocks.mock_profile(), mocks.mock_profile()],
                mock_regex_lookup='profile:.*',
            )
            self._execute_test_cases('join_group', test_cases, test_func=test)

    def test_add_to_group(self, *patches):
        profiles = [mocks.mock_profile(organization_id=self.by_profile.organization_id)]
        test_cases = [
            {
                'setup:group:id': fuzzy.FuzzyUUID().fuzz(),
                'setup:group:settings:whoCanInvite': 'ALL_MANAGERS_CAN_INVITE',
                'provider_func_args:0': profiles,
                'provider_func_args:1': 'setup:group:id',
                'setup:membership:role': 'OWNER',
                'setup:membership:profile_id': self.by_profile.id,
                'assertions:has_response': True,
            },
            {
                'setup:group:id': fuzzy.FuzzyUUID().fuzz(),
                'provider_func_args:0': profiles,
                'provider_func_args:1': 'setup:group:id',
                'setup:group:settings:whoCanInvite': 'ALL_MANAGERS_CAN_INVITE',
                'setup:membership:role': 'MANAGER',
                'setup:membership:profile_id': self.by_profile.id,
                'assertions:has_response': True,
            },
            {
                'setup:group:id': fuzzy.FuzzyUUID().fuzz(),
                'provider_func_args:0': profiles,
                'provider_func_args:1': 'setup:group:id',
                'setup:group:settings:whoCanInvite': 'ALL_MANAGERS_CAN_INVITE',
                'setup:membership:role': 'MEMBER',
                'setup:membership:profile_id': self.by_profile.id,
                'assertions:has_response': False,
            },
            {
                'setup:group:id': fuzzy.FuzzyUUID().fuzz(),
                'provider_func_args:0': profiles,
                'provider_func_args:1': 'setup:group:id',
                'setup:group:settings:whoCanInvite': 'ALL_MEMBERS_CAN_INVITE',
                'setup:membership:role': 'OWNER',
                'setup:membership:profile_id': self.by_profile.id,
                'assertions:has_response': True,
            },
            {
                'setup:group:id': fuzzy.FuzzyUUID().fuzz(),
                'provider_func_args:0': profiles,
                'provider_func_args:1': 'setup:group:id',
                'setup:group:settings:whoCanInvite': 'ALL_MEMBERS_CAN_INVITE',
                'setup:membership:role': 'MANAGER',
                'setup:membership:profile_id': self.by_profile.id,
                'assertions:has_response': True,
            },
            {
                'setup:group:id': fuzzy.FuzzyUUID().fuzz(),
                'provider_func_args:0': profiles,
                'provider_func_args:1': 'setup:group:id',
                'setup:group:settings:whoCanInvite': 'ALL_MEMBERS_CAN_INVITE',
                'setup:membership:role': 'MEMBER',
                'setup:membership:profile_id': self.by_profile.id,
                'assertions:has_response': True,
            },
            {
                'setup:group:id': fuzzy.FuzzyUUID().fuzz(),
                'provider_func_args:0': profiles,
                'provider_func_args:1': 'setup:group:id',
                'setup:group:settings:whoCanInvite': 'ALL_MEMBERS_CAN_INVITE',
                'assertions:has_response': False,
            },
            {
                'setup:group:id': fuzzy.FuzzyUUID().fuzz(),
                'provider_func_args:0': profiles,
                'provider_func_args:1': 'setup:group:id',
                'setup:group:settings:whoCanInvite': 'ALL_MANAGERS_CAN_INVITE',
                'assertions:has_response': False,
            },
        ]

        expected = [provider_factories.GoogleGroupMemberFactory.create(
            email=profile.email,
            role='MEMBER',
        ).as_dict() for profile in profiles]
        with patch.object(self.provider, '_add_to_group') as mock_add_to_group:
            mock_add_to_group.return_value = expected

            def test(assertions, result, **kwargs):
                if assertions.get('has_response'):
                    test_case = kwargs['test_case']
                    self.assertEqual(mock_add_to_group.call_count, 1)
                    members = models.GoogleGroupMember.objects.filter(
                        profile_id__in=[profile.id for profile in profiles],
                        group_id=test_case['setup']['group']['id'],
                    )
                    group = models.GoogleGroup.objects.get(pk=test_case['setup']['group']['id'])
                    self.assertEqual(group.direct_members_count, len(expected))
                    self.assertEqual(len(members), len(expected))
                mock_add_to_group.reset_mock()
            self._execute_test_cases('add_profiles_to_group', test_cases, test_func=test)

    def test_approve_request_to_join(self, *patches):
        request = model_factories.GroupMembershipRequestFactory(
            approver_profile_ids=[self.by_profile.id, fuzzy.FuzzyUUID().fuzz()],
        )

        test_cases = [
            {
                'setup:group:id': request.group_id,
                'setup:members': [{'role': 'OWNER', 'profile_id': self.by_profile.id}],
                'provider_func_args:0': request,
                'assertions:result:status': group_containers.APPROVED,
            },
            {
                'setup:group:id': request.group_id,
                'setup:members': [{'role': 'MANAGER', 'profile_id': self.by_profile.id}],
                'provider_func_args:0': request,
                'assertions:result:status': group_containers.APPROVED,
            },
            {
                'setup:group:id': request.group_id,
                'setup:members': [{'role': 'MEMBER', 'profile_id': self.by_profile.id}],
                'provider_func_args:0': request,
                'assertions:raises': exceptions.Unauthorized,
            },
            {
                'setup:group:id': request.group_id,
                'setup:members': [{'role': 'OWNER'}],
                'provider_func_args:0': request,
                'assertions:raises': exceptions.Unauthorized,
            },
        ]

        def test(assertions, result, **kwargs):
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


@unittest.skip('skip')
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

        with self.mock_transport() as mock:
            mock_profiles = [
                mocks.mock_profile(id=member.profile_id,) for member in fixtures.get('members', [])
            ]
            mock.instance.register_mock_object(
                service='profile',
                action='get_profiles',
                return_object_path='profiles',
                return_object=mock_profiles,
                mock_regex_lookup='profile:get_profiles:.*',
            )
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

    def test_get_members(self, *patches):
        test_cases = [
            # all in domain can view, not a member
            {
                'setup:group:id': fuzzy.FuzzyUUID().fuzz(),
                'setup:group:settings:whoCanViewMembership': 'ALL_IN_DOMAIN_CAN_VIEW',
                'setup:members': [{'role': 'MEMBER'}],
                'provider_func_args:0': 'setup:group:id',
                'provider_func_args:1': group_containers.MEMBER,
                'assertions:members': lambda x: self.assertEqual(len(x), 1),
            },
            # members only can view, not a member
            {
                'setup:group:id': fuzzy.FuzzyUUID().fuzz(),
                'setup:group:settings:whoCanViewMembership': 'ALL_MEMBERS_CAN_VIEW',
                'setup:members': [{'role': 'MEMBER'}],
                'provider_func_args:0': 'setup:group:id',
                'provider_func_args:1': group_containers.MEMBER,
                'assertions:members': lambda x: self.assertEqual(len(x), 0),
            },
            # managers only can view, not a member
            {
                'setup:group:id': fuzzy.FuzzyUUID().fuzz(),
                'setup:group:settings:whoCanViewMembership': 'ALL_MANAGERS_CAN_VIEW',
                'setup:members': [{'role': 'MEMBER'}],
                'provider_func_args:0': 'setup:group:id',
                'provider_func_args:1': group_containers.MEMBER,
                'assertions:members': lambda x: self.assertEqual(len(x), 0),
            },
            # all in domain can view, a member
            {
                'setup:group:id': fuzzy.FuzzyUUID().fuzz(),
                'setup:group:settings:whoCanViewMembership': 'ALL_IN_DOMAIN_CAN_VIEW',
                'setup:members': [
                    {'role': 'MEMBER', 'profile_id': self.by_profile.id},
                    {'role': 'MEMBER'},
                ],
                'provider_func_args:0': 'setup:group:id',
                'provider_func_args:1': group_containers.MEMBER,
                'assertions:members': lambda x: self.assertEqual(len(x), 2),
            },
            # members only can view, a member
            {
                'setup:group:id': fuzzy.FuzzyUUID().fuzz(),
                'setup:group:settings:whoCanViewMembership': 'ALL_MEMBERS_CAN_VIEW',
                'setup:members': [
                    {'role': 'MEMBER', 'profile_id': self.by_profile.id},
                    {'role': 'MEMBER'},
                ],
                'provider_func_args:0': 'setup:group:id',
                'provider_func_args:1': group_containers.MEMBER,
                'assertions:members': lambda x: self.assertEqual(len(x), 2),
            },
            # managers only can view, a member
            {
                'setup:group:id': fuzzy.FuzzyUUID().fuzz(),
                'setup:group:settings:whoCanViewMembership': 'ALL_MANAGERS_CAN_VIEW',
                'setup:members': [
                    {'role': 'MEMBER', 'profile_id': self.by_profile.id},
                    {'role': 'MEMBER'},
                ],
                'setup:membership:role': 'MEMBER',
                'setup:membership:profile_id': self.by_profile.id,
                'provider_func_args:0': 'setup:group:id',
                'provider_func_args:1': group_containers.MEMBER,
                'assertions:members': lambda x: self.assertEqual(len(x), 0),
            },
            # all in domain can view, a manager
            {
                'setup:group:id': fuzzy.FuzzyUUID().fuzz(),
                'setup:group:settings:whoCanViewMembership': 'ALL_IN_DOMAIN_CAN_VIEW',
                'setup:members': [
                    {'role': 'MANAGER', 'profile_id': self.by_profile.id},
                    {'role': 'MEMBER'},
                ],
                'provider_func_args:0': 'setup:group:id',
                'provider_func_args:1': group_containers.MEMBER,
                'assertions:members': lambda x: self.assertEqual(len(x), 1),
            },
            # members only can view, a manager
            {
                'setup:group:id': fuzzy.FuzzyUUID().fuzz(),
                'setup:group:settings:whoCanViewMembership': 'ALL_MEMBERS_CAN_VIEW',
                'setup:members': [
                    {'role': 'MANAGER', 'profile_id': self.by_profile.id},
                    {'role': 'MEMBER'},
                ],
                'provider_func_args:0': 'setup:group:id',
                'provider_func_args:1': group_containers.MEMBER,
                'assertions:members': lambda x: self.assertEqual(len(x), 1),
            },
            # managers only can view, a manager
            {
                'setup:group:id': fuzzy.FuzzyUUID().fuzz(),
                'setup:group:settings:whoCanViewMembership': 'ALL_MANAGERS_CAN_VIEW',
                'setup:members': [
                    {'role': 'MANAGER', 'profile_id': self.by_profile.id},
                    {'role': 'MEMBER'},
                ],
                'provider_func_args:0': 'setup:group:id',
                'provider_func_args:1': group_containers.MEMBER,
                'assertions:members': lambda x: self.assertEqual(len(x), 1),
            },
            # all in domain can view, a owner
            {
                'setup:group:id': fuzzy.FuzzyUUID().fuzz(),
                'setup:group:settings:whoCanViewMembership': 'ALL_IN_DOMAIN_CAN_VIEW',
                'setup:members': [
                    {'role': 'OWNER', 'profile_id': self.by_profile.id},
                    {'role': 'MEMBER'},
                ],
                'provider_func_args:0': 'setup:group:id',
                'provider_func_args:1': group_containers.MEMBER,
                'assertions:members': lambda x: self.assertEqual(len(x), 1),
            },
            # members only can view, a owner
            {
                'setup:group:id': fuzzy.FuzzyUUID().fuzz(),
                'setup:group:settings:whoCanViewMembership': 'ALL_MEMBERS_CAN_VIEW',
                'setup:members': [
                    {'role': 'OWNER', 'profile_id': self.by_profile.id},
                    {'role': 'MEMBER'},
                ],
                'provider_func_args:0': 'setup:group:id',
                'provider_func_args:1': group_containers.MEMBER,
                'assertions:members': lambda x: self.assertEqual(len(x), 1),
            },
            # managers only can view, a owner
            {
                'setup:group:id': fuzzy.FuzzyUUID().fuzz(),
                'setup:group:settings:whoCanViewMembership': 'ALL_MANAGERS_CAN_VIEW',
                'setup:members': [
                    {'role': 'OWNER', 'profile_id': self.by_profile.id},
                    {'role': 'MEMBER'},
                ],
                'provider_func_args:0': 'setup:group:id',
                'provider_func_args:1': group_containers.MEMBER,
                'assertions:members': lambda x: self.assertEqual(len(x), 1),
            },
        ]
        self._execute_test_cases('get_members_for_group', test_cases)


@unittest.skip('skip')
@patch('group.providers.google.provider.service.control.get_object')
@patch('group.providers.google.provider.SignedJwtAssertionCredentials')
class TestGoogleGroups(BaseGoogleCase):

    def test_leave_group_not_a_member(self, *patches):
        group = model_factories.GoogleGroupFactory.create(
            organization_id=self.by_profile.organization_id,
        )
        with patch('group.providers.google.provider.build') as patched_build_api:
            patched_build_api().members().delete().execute.side_effect = HttpError('404', 'Error')
            self.provider.leave_group(group.id)

    def test_leave_group_all_members_can_leave(self, *patches):
        membership = model_factories.GoogleGroupMemberFactory.create(
            profile_id=self.by_profile.id,
            organization_id=self.by_profile.organization_id,
            group__direct_members_count=2,
            group__settings={'whoCanLeaveGroup': 'ALL_MEMBERS_CAN_LEAVE'},
        )
        with patch('group.providers.google.provider.build') as patched_build_api:
            patched_build_api().members().delete.execute.return_value = ''
            self.provider.leave_group(membership.group_id)
        self.assertEqual(patched_build_api().members().delete().execute.call_count, 1)
        self.assertFalse(
            models.GoogleGroupMember.objects.filter(profile_id=self.by_profile.id).exists()
        )
        self.assertEqual(
            models.GoogleGroup.objects.get(pk=membership.group_id).direct_members_count,
            1,
        )

    def test_leave_group_member_managers_can_only_leave(self, *patches):
        membership = model_factories.GoogleGroupMemberFactory.create(
            profile_id=self.by_profile.id,
            organization_id=self.by_profile.organization_id,
            role='MEMBER',
            group__direct_members_count=2,
            group__settings={'whoCanLeaveGroup': 'ALL_MANAGERS_CAN_LEAVE'},
        )
        with self.assertRaises(exceptions.Unauthorized):
            self.provider.leave_group(membership.group_id)
        self.assertTrue(
            models.GoogleGroupMember.objects.filter(profile_id=self.by_profile.id).exists()
        )
        self.assertEqual(
            models.GoogleGroup.objects.get(pk=membership.group_id).direct_members_count,
            2,
        )

    def test_leave_group_manager_managers_can_only_leave(self, *patches):
        membership = model_factories.GoogleGroupMemberFactory.create(
            profile_id=self.by_profile.id,
            organization_id=self.by_profile.organization_id,
            role='MANAGER',
            group__direct_members_count=2,
            group__settings={'whoCanLeaveGroup': 'ALL_MANAGERS_CAN_LEAVE'},
        )
        with patch('group.providers.google.provider.build') as patched_build_api:
            patched_build_api().members().delete.execute.return_value = ''
            self.provider.leave_group(membership.group_id)
        self.assertEqual(patched_build_api().members().delete().execute.call_count, 1)
        self.assertFalse(
            models.GoogleGroupMember.objects.filter(profile_id=self.by_profile.id).exists()
        )
        self.assertEqual(
            models.GoogleGroup.objects.get(pk=membership.group_id).direct_members_count,
            1,
        )

    def test_join_group_only_one_pending_request_per_group(self, *patches):
        group = model_factories.GoogleGroupFactory.create(
            settings={'whoCanJoin': 'CAN_REQUEST_TO_JOIN'},
        )
        membership_request = self.provider.join_group(group.id)
        self.assertEqual(membership_request.status, group_containers.PENDING)
        with self.assertRaises(exceptions.AlreadyRequested):
            self.provider.join_group(group.id)
