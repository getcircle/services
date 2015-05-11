from mock import patch
import service.control

from services.test import (
    fuzzy,
    mocks,
    TestCase,
)
from protobufs.services.group import containers_pb2 as group_containers


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
            self.client.call_action('list_members', group_id=fuzzy.FuzzyUUID().fuzz())

    def test_list_members_group_id_required(self):
        with self.assertFieldError('group_id', 'MISSING'):
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
                group_id='group@circlehq.co',
            )
        self.assertEqual(len(response.result.members), len(mock_members))
        for member in response.result.members:
            self.assertEqual(member.role, group_containers.GOOGLE)