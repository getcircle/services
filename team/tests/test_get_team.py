import arrow

from protobufs.services.team import containers_pb2 as team_containers
import service.control

from services.test import (
    mocks,
    MockedTestCase,
)

from .. import factories


class Test(MockedTestCase):

    def setUp(self):
        super(Test, self).setUp()
        self.organization = mocks.mock_organization()
        self.profile = mocks.mock_profile(organization_id=self.organization.id)
        self.token = mocks.mock_token(
            organization_id=self.organization.id,
            profile_id=self.profile.id,
        )
        self.client = service.control.Client('team', token=self.token)
        self.mock.instance.dont_mock_service('team')

    def test_get_team_team_id_required(self):
        with self.assertFieldError('team_id', 'MISSING'):
            self.client.call_action('get_team')

    def test_get_team_team_id_invalid(self):
        with self.assertFieldError('team_id', 'INVALID'):
            self.client.call_action('get_team', team_id='invalid')

    def test_get_team_wrong_organization(self):
        team = factories.TeamFactory.create()
        with self.assertFieldError('team_id', 'DOES_NOT_EXIST'):
            self.client.call_action('get_team', team_id=str(team.id))

    def test_get_team(self):
        profile = mocks.mock_profile()
        self.mock.instance.register_mock_object(
            service='profile',
            action='get_profile',
            return_object_path='profile',
            return_object=profile,
            profile_id=profile.id,
            inflations={'disabled': True},
        )
        expected = factories.TeamFactory.create_protobuf(
            description=mocks.mock_description(by_profile_id=profile.id),
            organization_id=self.organization.id,
        )
        response = self.client.call_action('get_team', team_id=expected.id)
        self.verify_containers(expected, response.result.team, ignore_fields=('description',))
        description = response.result.team.description
        self.verify_containers(profile, description.by_profile)

    def test_get_team_dont_inflate_profile(self):
        profile = mocks.mock_profile()
        self.mock.instance.register_mock_object(
            service='profile',
            action='get_profile',
            return_object_path='profile',
            return_object=profile,
            profile_id=profile.id,
            inflations={'disabled': True},
        )
        expected = factories.TeamFactory.create_protobuf(
            description=mocks.mock_description(by_profile_id=profile.id),
            organization_id=self.organization.id,
        )
        response = self.client.call_action(
            'get_team',
            team_id=expected.id,
            inflations={'disabled': True},
        )
        self.verify_containers(expected, response.result.team)
        self.assertEqual(response.result.team.description.by_profile.ByteSize(), 0)

    def test_get_team_permissions_member(self):
        team = factories.TeamFactory.create(organization_id=self.organization.id)
        factories.TeamMemberFactory.create(
            team=team,
            organization_id=self.organization.id,
            profile_id=self.profile.id,
        )
        response = self.client.call_action('get_team', team_id=str(team.id))
        self.assertTrue(response.result.is_member)
        permissions = response.result.team.permissions
        self.assertFalse(permissions.can_edit)
        self.assertFalse(permissions.can_delete)
        self.assertTrue(permissions.can_add)

    def test_get_team_permissions_coordinator(self):
        team = factories.TeamFactory.create(organization_id=self.organization.id)
        factories.TeamMemberFactory.create(
            team=team,
            organization_id=self.organization.id,
            profile_id=self.profile.id,
            role=team_containers.TeamMemberV1.COORDINATOR,
        )
        response = self.client.call_action('get_team', team_id=str(team.id))
        self.assertTrue(response.result.is_member)
        permissions = response.result.team.permissions
        self.assertTrue(permissions.can_edit)
        self.assertTrue(permissions.can_delete)
        self.assertTrue(permissions.can_add)

    def test_get_team_permissions_not_member(self):
        team = factories.TeamFactory.create(organization_id=self.organization.id)
        factories.TeamMemberFactory.create(
            team=team,
            organization_id=self.organization.id,
        )
        response = self.client.call_action('get_team', team_id=str(team.id))
        self.assertFalse(response.result.is_member)
        permissions = response.result.team.permissions
        self.assertFalse(permissions.can_edit)
        self.assertFalse(permissions.can_delete)
        self.assertFalse(permissions.can_add)

    def test_get_team_permissions_admin(self):
        self.profile.is_admin = True
        self.mock.instance.register_mock_object(
            service='profile',
            action='get_profile',
            return_object_path='profile',
            return_object=self.profile,
            profile_id=self.profile.id,
            inflations={'disabled': True},
            fields={'only': ['is_admin']},
        )
        team = factories.TeamFactory.create(organization_id=self.organization.id)
        factories.TeamMemberFactory.create(
            team=team,
            organization_id=self.organization.id,
        )
        response = self.client.call_action('get_team', team_id=str(team.id))
        self.assertFalse(response.result.is_member)
        permissions = response.result.team.permissions
        self.assertTrue(permissions.can_edit)
        self.assertTrue(permissions.can_delete)
        self.assertTrue(permissions.can_add)

    def test_get_team_contact_methods(self):
        team = factories.TeamFactory.create(organization_id=self.organization.id)
        first_contact_method = factories.ContactMethodFactory.create(
            team=team,
            created=arrow.Arrow(2016, 2, 1).datetime,
        )
        last_contact_method = factories.ContactMethodFactory.create(
            team=team,
            created=arrow.Arrow(2016, 2, 2).datetime,
        )
        response = self.client.call_action('get_team', team_id=str(team.id))
        contact_methods = response.result.team.contact_methods
        self.verify_containers(contact_methods[0], first_contact_method)
        self.verify_containers(contact_methods[1], last_contact_method)
