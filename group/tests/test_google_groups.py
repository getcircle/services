from mock import patch
import service.control

from services.test import (
    fuzzy,
    mocks,
    TestCase,
)
from protobufs.services.group import containers_pb2 as group_containers

from .. import factories


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
            mocks.mock_member(role=group_containers.GOOGLE),
            mocks.mock_member(role=group_containers.GOOGLE),
        ]
        mock_google_provider().list_members_for_group.return_value = mock_members
        with self.mock_transport() as mock:
            self._mock_token_objects(mock)
            mock.instance.register_mock_object(
                service='profile',
                action='get_profiles',
                return_object_path='profiles',
                return_object=[x.profile for x in mock_members],
                emails=[x.profile.email for x in mock_members],
            )
            response = self.client.call_action(
                'list_members',
                provider=group_containers.GOOGLE,
                group_key='group@circlehq.co',
            )
        self.assertEqual(len(response.result.members), len(mock_members))
        for member in response.result.members:
            self.assertEqual(member.role, group_containers.GOOGLE)

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
