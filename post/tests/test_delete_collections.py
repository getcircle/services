from protobufs.services.team import containers_pb2 as team_containers
from protobufs.services.post import containers_pb2 as post_containers
import service.control

from services.test import (
    fuzzy,
    mocks,
    MockedTestCase,
)

from .. import (
    factories,
    models,
)

from .helpers import mock_get_teams


class Test(MockedTestCase):

    def setUp(self):
        super(Test, self).setUp()
        self.organization = mocks.mock_organization()
        self.profile = mocks.mock_profile(organization_id=self.organization.id)
        self.team = mocks.mock_team(organization_id=self.organization.id)
        token = mocks.mock_token(organization_id=self.organization.id, profile_id=self.profile.id)
        self.client = service.control.Client('post', token=token)
        self.mock.instance.dont_mock_service('post')

        factories.CollectionFactory.reset_sequence()

    def test_delete_collections_owner_id_required(self):
        with self.assertFieldError('owner_id', 'MISSING'):
            self.client.call_action('delete_collections', owner_type=post_containers.CollectionV1.PROFILE)

    def test_delete_collections_owner_id_invalid(self):
        with self.assertFieldError('owner_id'):
            self.client.call_action('delete_collections', owner_type=post_containers.CollectionV1.PROFILE, owner_id=fuzzy.text())

    def test_delete_collections_owned_by_team_not_member(self):
        mock_get_teams(self.mock.instance, [self.team])
        collection = factories.CollectionFactory.create_protobuf(team=self.team)
        with self.assertRaisesCallActionError() as expected:
            self.client.call_action('delete_collections', owner_type=post_containers.CollectionV1.TEAM, owner_id=self.team.id)

        self.assertIn('PERMISSION_DENIED', expected.exception.response.errors)

    def test_delete_collections_owned_by_team_member(self):
        mock_get_teams(self.mock.instance, [self.team], role=team_containers.TeamMemberV1.MEMBER)
        collection = factories.CollectionFactory.create_protobuf(team=self.team)
        with self.assertRaisesCallActionError() as expected:
            self.client.call_action('delete_collections', owner_type=post_containers.CollectionV1.TEAM, owner_id=self.team.id)

        self.assertIn('PERMISSION_DENIED', expected.exception.response.errors)

    def test_delete_collections_owned_by_team_coordinator(self):
        mock_get_teams(
            self.mock.instance,
            [self.team],
            role=team_containers.TeamMemberV1.COORDINATOR,
        )
        first_collection = factories.CollectionFactory.create_protobuf(team=self.team)
        second_collection = factories.CollectionFactory.create_protobuf(team=self.team)
        self.client.call_action(
            'delete_collections',
            owner_type=post_containers.CollectionV1.TEAM,
            owner_id=self.team.id
        )
        collections = list(models.Collection.objects.filter(
            organization_id=self.team.organization_id,
            owner_type=post_containers.CollectionV1.TEAM,
            owner_id=self.team.id
        ))
        self.assertTrue(len(collections) == 0)
