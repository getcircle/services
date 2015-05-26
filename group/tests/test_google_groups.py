from mock import patch
import service.control

from services.test import (
    fuzzy,
    mocks,
    TestCase,
)
from protobufs.services.group import containers_pb2 as group_containers
from protobufs.services.group.actions import respond_to_membership_request_pb2

from .. import (
    factories,
    models,
)


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

    def test_list_groups_provider_required(self):
        with self.assertFieldError('provider', 'MISSING'):
            self.client.call_action('list_groups')

    @patch('group.actions.providers.Google')
    def test_list_groups_for_organization(self, mock_google_provider):
        mock_google_provider().list_groups_for_organization.return_value = [
            mocks.mock_group(),
            mocks.mock_group(),
        ]
        with self.mock_transport() as mock:
            self._mock_token_objects(mock)
            response = self.client.call_action('list_groups', provider=group_containers.GOOGLE)
        self.assertEqual(len(response.result.groups), 2)

    @patch('group.actions.providers.Google')
    def test_list_groups_for_profile(self, mock_google_provider):
        mock_groups = [
            mocks.mock_group(),
            mocks.mock_group(),
        ]
        mock_google_provider().list_groups_for_profile.return_value = mock_groups
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
                'list_groups',
                provider=group_containers.GOOGLE,
                profile_id=for_profile.id,
            )
        self.assertEqual(len(response.result.groups), len(mock_groups))

    def test_list_members_provider_required(self):
        with self.assertFieldError('provider', 'MISSING'):
            self.client.call_action('list_members', group_key=fuzzy.FuzzyUUID().fuzz())

    def test_list_members_group_key_required(self):
        with self.assertFieldError('group_key', 'MISSING'):
            self.client.call_action('list_members', provider=group_containers.GOOGLE)

    @patch('group.actions.providers.Google')
    def test_list_members(self, mock_google_provider):
        mock_members = [
            mocks.mock_member(role=group_containers.MEMBER),
            mocks.mock_member(role=group_containers.MEMBER),
            mocks.mock_member(role=group_containers.MEMBER, should_mock_profile=False),
        ]
        mock_google_provider().list_members_for_group.return_value = mock_members
        with self.mock_transport() as mock:
            self._mock_token_objects(mock)
            mock.instance.register_mock_object(
                service='profile',
                action='get_profiles',
                return_object_path='profiles',
                return_object=[x.profile for x in mock_members[:-1]],
                emails=[x.profile.email for x in mock_members],
            )
            response = self.client.call_action(
                'list_members',
                provider=group_containers.GOOGLE,
                group_key='group@circlehq.co',
            )
        self.assertEqual(len(response.result.members), len(mock_members) - 1)
        for member in response.result.members:
            self.assertEqual(member.role, group_containers.MEMBER)

    def test_get_group_group_key_required(self):
        with self.assertFieldError('group_key', 'MISSING'):
            self.client.call_action('get_group')

    @patch('group.actions.providers.Google')
    def test_get_group_not_found(self, mock_google_provider):
        mock_google_provider().get_group.return_value = None
        with self.mock_transport() as mock:
            self._mock_token_objects(mock)
            response = self.client.call_action('get_group', group_key='group@criclehq.co')
        self.assertFalse(response.result.HasField('group'))

    @patch('group.actions.providers.Google')
    def test_get_group(self, mock_google_provider):
        mock_group = mocks.mock_group()
        mock_google_provider().get_group.return_value = mock_group
        with self.mock_transport() as mock:
            self._mock_token_objects(mock)
            response = self.client.call_action('get_group', group_key=mock_group.email)

        self.verify_containers(mock_group, response.result.group)

    def test_leave_group_no_group_key(self):
        with self.mock_transport() as mock:
            self._mock_token_objects(mock)
            with self.assertFieldError('group_key', 'MISSING'):
                self.client.call_action('leave_group')

    @patch('group.actions.providers.Google')
    def test_leave_group(self, mock_google_provider):
        with self.mock_transport() as mock:
            self._mock_token_objects(mock)
            self.client.call_action('leave_group', group_key='group@circlehq.co')

    def test_join_group_group_key_required(self):
        with self.mock_transport() as mock:
            self._mock_token_objects(mock)
            with self.assertFieldError('group_key', 'MISSING'):
                self.client.call_action('join_group')

    @patch('group.actions.providers.Google')
    def test_join_group(self, mock_google_provider):
        expected_request = factories.GroupMembershipRequestFactory.create()
        mock_google_provider().join_group.return_value = expected_request
        with self.mock_transport() as mock:
            self._mock_token_objects(mock)
            response = self.client.call_action('join_group', group_key='group@circlehq.co')
            self.assertEqual(response.result.request.status, expected_request.status)

    def test_respond_to_membership_request_request_id_required(self):
        with self.assertFieldError('request_id', 'MISSING'):
            self.client.call_action(
                'respond_to_membership_request',
                action=respond_to_membership_request_pb2.RequestV1.APPROVE,
            )

    def test_respond_to_membership_request_action_required(self):
        with self.assertFieldError('action', 'MISSING'):
            self.client.call_action(
                'respond_to_membership_request',
                request_id=fuzzy.FuzzyUUID().fuzz(),
            )

    def test_respond_to_membership_request_request_id_invalid(self):
        with self.assertFieldError('request_id', 'INVALID'):
            self.client.call_action(
                'respond_to_membership_request',
                request_id='invalid',
                action=respond_to_membership_request_pb2.RequestV1.APPROVE,
            )

    def test_respond_to_membership_request_request_id_does_not_exist(self):
        with self.assertFieldError('request_id', 'DOES_NOT_EXIST'):
            self.client.call_action(
                'respond_to_membership_request',
                request_id=fuzzy.FuzzyUUID().fuzz(),
                action=respond_to_membership_request_pb2.RequestV1.APPROVE,
            )

    @patch('group.actions.providers.Google')
    def test_respond_to_membership_request_approve(self, mock_google_provider):
        member_request = factories.GroupMembershipRequestFactory.create(
            status=group_containers.PENDING,
        )
        with self.mock_transport() as mock:
            self._mock_token_objects(mock)
            self.client.call_action(
                'respond_to_membership_request',
                request_id=str(member_request.id),
                action=respond_to_membership_request_pb2.RequestV1.APPROVE,
            )
        self.assertEqual(mock_google_provider().approve_request_to_join.call_count, 1)

    @patch('group.actions.providers.Google')
    def test_respond_to_membership_request_denied(self, mock_google_provider):
        member_request = factories.GroupMembershipRequestFactory.create(
            status=group_containers.PENDING,
        )
        with self.mock_transport() as mock:
            self._mock_token_objects(mock)
            self.client.call_action(
                'respond_to_membership_request',
                request_id=str(member_request.id),
                action=respond_to_membership_request_pb2.RequestV1.DENY,
            )
        self.assertEqual(mock_google_provider().deny_request_to_join.call_count, 1)

    def test_add_to_group_group_key_required(self):
        with self.mock_transport() as mock, self.assertFieldError('group_key', 'MISSING'):
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
                group_key='group@circlehq.co',
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
                group_key='group@circlehq.co',
                profile_ids=profile_ids,
            )
            self.assertEqual(len(response.result.new_members), 2)

    def test_get_membership_requests(self):
        # Create membership requests where by_profile is an approver
        factories.GroupMembershipRequestFactory.create_batch(
            size=2,
            approver_profile_ids=[self.by_profile.id, fuzzy.FuzzyUUID().fuzz()],
        )
        # Create membership requests where by_profile is not an approver
        factories.GroupMembershipRequestFactory.create_batch(
            size=2,
            approver_profile_ids=[fuzzy.FuzzyUUID().fuzz()],
        )
        with self.mock_transport() as mock:
            self._mock_token_objects(mock)
            response = self.client.call_action('get_membership_requests')
            self.assertEqual(len(response.result.requests), 2)
