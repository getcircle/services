from mock import patch
import service.control
import unittest

from services.test import (
    fuzzy,
    mocks,
    TestCase,
)
from protobufs.services.group import containers_pb2 as group_containers
from protobufs.services.group.actions import respond_to_membership_request_pb2

from ..factories import models as model_factories


@unittest.skip('skip')
class TestGoogleGroups(TestCase):

    def setUp(self):
        super(TestGoogleGroups, self).setUp()
        self.organization = mocks.mock_organization(domain='circlehq.co')
        self.by_profile = mocks.mock_profile(email='ravi@circlehq.co')
        self.client = service.control.Client(
            'group',
            token=mocks.mock_token(
                organization_id=self.organization.id,
                profile_id=self.by_profile.id,
            ),
        )

    def _mock_token_objects(self, mock):
        mock.instance.register_empty_response(
            service='organization',
            action='get_integration',
            mock_regex_lookup='organization:get_integration:.*',
        )
        mock.instance.register_mock_object(
            service='organization',
            action='get_organization',
            return_object_path='organization',
            return_object=self.organization,
            organization_id=self.organization.id,
        )
        mock.instance.register_mock_object(
            service='profile',
            action='get_profile',
            return_object_path='profile',
            return_object=self.by_profile,
            profile_id=self.by_profile.id,
        )

    def test_get_groups_provider_required(self):
        with self.assertFieldError('provider', 'MISSING'):
            self.client.call_action('get_groups')

    @patch('group.actions.providers.Google')
    def test_get_groups_for_organization(self, mock_google_provider):
        mock_google_provider().get_groups_for_organization.return_value = [
            mocks.mock_group(),
            mocks.mock_group(),
        ]
        with self.mock_transport() as mock:
            self._mock_token_objects(mock)
            response = self.client.call_action('get_groups', provider=group_containers.GOOGLE)
        self.assertEqual(len(response.result.groups), 2)

    @patch('group.actions.providers.Google')
    def test_get_groups_for_profile(self, mock_google_provider):
        mock_groups = [
            mocks.mock_group(),
            mocks.mock_group(),
        ]
        mock_google_provider().get_groups_for_profile.return_value = mock_groups
        for_profile = mocks.mock_profile(email='michael@circlehq.co')
        with self.mock_transport() as mock:
            self._mock_token_objects(mock)
            mock.instance.register_mock_object(
                service='profile',
                action='get_profile',
                return_object_path='profile',
                return_object=for_profile,
                profile_id=for_profile.id,
            )
            response = self.client.call_action(
                'get_groups',
                provider=group_containers.GOOGLE,
                profile_id=for_profile.id,
            )
        self.assertEqual(
            mock_google_provider().get_groups_for_profile.call_args[0][0],
            for_profile,
        )
        self.assertEqual(len(response.result.groups), len(mock_groups))

    def test_get_members_provider_required(self):
        with self.assertFieldError('provider', 'MISSING'):
            self.client.call_action('get_members', group_id=fuzzy.FuzzyUUID().fuzz())

    def test_get_members_group_id_required(self):
        with self.assertFieldError('group_id', 'MISSING'):
            self.client.call_action('get_members', provider=group_containers.GOOGLE)

    def test_get_members_group_id_invalid(self):
        with self.assertFieldError('group_id'):
            self.client.call_action(
                'get_members',
                provider=group_containers.GOOGLE,
                group_id='invalid',
            )

    @patch('group.actions.providers.Google')
    def test_get_members(self, mock_google_provider):
        mock_members = [
            mocks.mock_member(role=group_containers.MEMBER),
            mocks.mock_member(role=group_containers.MEMBER),
        ]
        mock_google_provider().get_members_for_group.return_value = mock_members
        with self.mock_transport() as mock:
            self._mock_token_objects(mock)
            response = self.client.call_action(
                'get_members',
                provider=group_containers.GOOGLE,
                group_id=fuzzy.FuzzyUUID().fuzz(),
            )
        self.assertEqual(len(response.result.members), len(mock_members))
        for member in response.result.members:
            self.assertEqual(member.role, group_containers.MEMBER)

    def test_get_group_group_id_required(self):
        with self.assertFieldError('group_id', 'MISSING'):
            self.client.call_action('get_group')

    @patch('group.actions.providers.Google')
    def test_get_group(self, mock_google_provider):
        mock_group = mocks.mock_group()
        mock_google_provider().get_group.return_value = mock_group
        with self.mock_transport() as mock:
            self._mock_token_objects(mock)
            response = self.client.call_action(
                'get_group',
                group_id=mock_group.email,
                provider=group_containers.GOOGLE,
            )

        self.verify_containers(mock_group, response.result.group)

    @patch('group.actions.providers.Google')
    def test_get_group_does_not_exist(self, mock_google_provider):
        mock_google_provider().get_group.return_value = None
        with self.mock_transport() as mock, self.assertFieldError('group_id', 'DOES_NOT_EXIST'):
            self._mock_token_objects(mock)
            self.client.call_action(
                'get_group',
                group_id=fuzzy.FuzzyUUID().fuzz(),
                provider=group_containers.GOOGLE,
            )

    def test_leave_group_no_group_id(self):
        with self.mock_transport() as mock:
            self._mock_token_objects(mock)
            with self.assertFieldError('group_id', 'MISSING'):
                self.client.call_action('leave_group')

    def test_leave_group_no_provider(self):
        with self.mock_transport() as mock:
            self._mock_token_objects(mock)
            with self.assertFieldError('provider', 'MISSING'):
                self.client.call_action('leave_group', group_id=fuzzy.FuzzyUUID().fuzz())

    @patch('group.actions.providers.Google')
    def test_leave_group(self, mock_google_provider):
        with self.mock_transport() as mock:
            self._mock_token_objects(mock)
            self.client.call_action(
                'leave_group',
                group_id=fuzzy.FuzzyUUID().fuzz(),
                provider=group_containers.GOOGLE,
            )

    def test_join_group_group_id_required(self):
        with self.mock_transport() as mock:
            self._mock_token_objects(mock)
            with self.assertFieldError('group_id', 'MISSING'):
                self.client.call_action('join_group')

    def test_join_group_provider_required(self):
        with self.mock_transport() as mock:
            self._mock_token_objects(mock)
            with self.assertFieldError('provider', 'MISSING'):
                self.client.call_action('join_group', group_id=fuzzy.FuzzyUUID().fuzz())

    @patch('group.actions.providers.Google')
    def test_join_group_send_notification_when_pending(self, mock_google_provider):
        expected_request = model_factories.GroupMembershipRequestFactory.create(
            status=group_containers.PENDING,
        )
        mock_google_provider().join_group.return_value = expected_request
        with self.mock_transport() as mock:
            self._mock_token_objects(mock)
            mock.instance.register_empty_response(
                service='notification',
                action='send_notification',
                mock_regex_lookup='notification:.*',
            )
            response = self.client.call_action(
                'join_group',
                group_id='group@circlehq.co',
                provider=group_containers.GOOGLE,
            )
            self.assertEqual(response.result.request.status, expected_request.status)

    @patch('group.actions.providers.Google')
    def test_join_group_dont_send_notification_when_approved(self, mock_google_provider):
        expected_request = model_factories.GroupMembershipRequestFactory.create(
            status=group_containers.APPROVED,
        )
        mock_google_provider().join_group.return_value = expected_request
        with self.mock_transport() as mock:
            self._mock_token_objects(mock)
            response = self.client.call_action(
                'join_group',
                group_id=fuzzy.FuzzyUUID().fuzz(),
                provider=group_containers.GOOGLE,
            )
            self.assertEqual(response.result.request.status, expected_request.status)

    def test_respond_to_membership_request_request_id_required(self):
        with self.assertFieldError('request_id', 'MISSING'):
            self.client.call(
                'respond_to_membership_request',
                action_kwargs={'action': respond_to_membership_request_pb2.RequestV1.APPROVE},
            )

    def test_respond_to_membership_request_action_required(self):
        with self.assertFieldError('action', 'MISSING'):
            self.client.call_action(
                'respond_to_membership_request',
                request_id=fuzzy.FuzzyUUID().fuzz(),
            )

    def test_respond_to_membership_request_request_id_invalid(self):
        with self.assertFieldError('request_id', 'INVALID'):
            self.client.call(
                'respond_to_membership_request',
                action_kwargs={
                    'action': respond_to_membership_request_pb2.RequestV1.APPROVE,
                    'request_id': 'invalid',
                },
            )

    def test_respond_to_membership_request_request_id_does_not_exist(self):
        with self.assertFieldError('request_id', 'DOES_NOT_EXIST'):
            self.client.call(
                'respond_to_membership_request',
                action_kwargs={
                    'action': respond_to_membership_request_pb2.RequestV1.APPROVE,
                    'request_id': fuzzy.FuzzyUUID().fuzz(),
                },
            )

    @patch('group.actions.providers.Google')
    def test_respond_to_membership_request_approve(self, mock_google_provider):
        member_request = model_factories.GroupMembershipRequestFactory.create(
            status=group_containers.PENDING,
        )
        member_request.status = group_containers.APPROVED
        mock_google_provider().approve_request_to_join.return_value = member_request
        with self.mock_transport() as mock:
            self._mock_token_objects(mock)
            mock.instance.register_empty_response(
                service='notification',
                action='send_notification',
                mock_regex_lookup='notification:.*',
            )
            self.client.call(
                'respond_to_membership_request',
                action_kwargs={
                    'action': respond_to_membership_request_pb2.RequestV1.APPROVE,
                    'request_id': str(member_request.id),
                },
            )
        self.assertEqual(mock_google_provider().approve_request_to_join.call_count, 1)

    @patch('group.actions.providers.Google')
    def test_respond_to_membership_request_denied(self, mock_google_provider):
        member_request = model_factories.GroupMembershipRequestFactory.create(
            status=group_containers.PENDING,
        )
        member_request.status = group_containers.DENIED
        mock_google_provider().deny_request_to_join.return_value = member_request
        with self.mock_transport() as mock:
            self._mock_token_objects(mock)
            mock.instance.register_empty_response(
                service='notification',
                action='send_notification',
                mock_regex_lookup='notification:.*',
            )
            self.client.call(
                'respond_to_membership_request',
                action_kwargs={
                    'action': respond_to_membership_request_pb2.RequestV1.DENY,
                    'request_id': str(member_request.id),
                },
            )
        self.assertEqual(mock_google_provider().deny_request_to_join.call_count, 1)

    def test_add_to_group_group_id_required(self):
        with self.mock_transport() as mock, self.assertFieldError('group_id', 'MISSING'):
            self._mock_token_objects(mock)
            self.client.call_action(
                'add_to_group',
                profile_ids=[fuzzy.FuzzyUUID().fuzz()],
            )

    def test_add_to_group_profile_ids_invalid(self):
        with self.mock_transport() as mock, self.assertFieldError('profile_ids'):
            self._mock_token_objects(mock)
            self.client.call_action(
                'add_to_group',
                group_id='group@circlehq.co',
                provider=group_containers.GOOGLE,
                profile_ids=['invalid'],
            )

    @patch('group.actions.providers.Google')
    def test_add_to_group(self, mock_google_provider):
        profile_overrides = {'organization_id': self.by_profile.organization_id}
        members = [
            mocks.mock_member(profile_overrides=profile_overrides),
            mocks.mock_member(profile_overrides=profile_overrides),
        ]
        profiles = [member.profile for member in members]
        profile_ids = [profile.id for profile in profiles]
        mock_google_provider().add_profiles_to_group.return_value = members
        with self.mock_transport() as mock:
            self._mock_token_objects(mock)
            mock.instance.register_mock_object(
                service='profile',
                action='get_profiles',
                return_object_path='profiles',
                return_object=profiles,
                ids=profile_ids,
            )
            response = self.client.call_action(
                'add_to_group',
                group_id=fuzzy.FuzzyUUID().fuzz(),
                provider=group_containers.GOOGLE,
                profile_ids=profile_ids,
            )
            self.assertEqual(len(response.result.new_members), 2)

    def test_get_membership_requests(self):
        # Create membership requests where by_profile is an approver
        model_factories.GroupMembershipRequestFactory.create_batch(
            size=2,
            approver_profile_ids=[self.by_profile.id, fuzzy.FuzzyUUID().fuzz()],
        )
        # Create membership requests where by_profile is not an approver
        model_factories.GroupMembershipRequestFactory.create_batch(
            size=2,
            approver_profile_ids=[fuzzy.FuzzyUUID().fuzz()],
        )
        with self.mock_transport() as mock:
            self._mock_token_objects(mock)
            response = self.client.call_action('get_membership_requests')
            self.assertEqual(len(response.result.requests), 2)

    def test_get_membership_requests_pending_only(self):
        # Create membership requests that are pending
        model_factories.GroupMembershipRequestFactory.create_batch(
            size=2,
            approver_profile_ids=[self.by_profile.id, fuzzy.FuzzyUUID().fuzz()],
            status=group_containers.PENDING,
        )
        # Create membership requests that are approved
        model_factories.GroupMembershipRequestFactory.create_batch(
            size=2,
            approver_profile_ids=[self.by_profile.id, fuzzy.FuzzyUUID().fuzz()],
            status=group_containers.APPROVED,
        )
        model_factories.GroupMembershipRequestFactory.create_batch(
            size=2,
            approver_profile_ids=[self.by_profile.id, fuzzy.FuzzyUUID().fuzz()],
            status=group_containers.DENIED,
        )
        with self.mock_transport() as mock:
            self._mock_token_objects(mock)
            response = self.client.call_action(
                'get_membership_requests',
                status=group_containers.PENDING,
            )
            self.assertEqual(len(response.result.requests), 2)
